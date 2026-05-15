from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from runtime.event_contracts import (
    build_backend_event_envelope,
    build_runtime_rejection_payload,
    normalize_frontend_command,
)
from browser import arm_picker

if TYPE_CHECKING:
    from agent import AgentLoop


def _is_closed_websocket_error(exc: BaseException) -> bool:
    if isinstance(exc, WebSocketDisconnect):
        return True
    if isinstance(exc, RuntimeError):
        error_text = str(exc)
        return "close message has been sent" in error_text or 'Cannot call "send"' in error_text
    return exc.__class__.__name__ == "ClientDisconnected"


async def _send_replay_json(ws: WebSocket, agent: Any, payload: dict[str, Any]) -> bool:
    if getattr(agent, "_ws_disconnected", False):
        if str(payload.get("type") or "").startswith("replay") and not getattr(agent, "_ws_disconnect_logged", False):
            setattr(agent, "_ws_disconnect_logged", True)
            print("[WS] disconnected during replay_all; stopping result send")
        return False

    try:
        await ws.send_json(payload)
        return True
    except WebSocketDisconnect:
        setattr(agent, "_ws_disconnected", True)
        setattr(agent, "_ws_disconnect_logged", True)
        print("[WS] disconnected during replay_all; stopping result send")
        return False
    except RuntimeError as exc:
        if not _is_closed_websocket_error(exc):
            raise
        setattr(agent, "_ws_disconnected", True)
        setattr(agent, "_ws_disconnect_logged", True)
        print("[WS] disconnected during replay_all; stopping result send")
        return False
    except Exception as exc:
        if exc.__class__.__name__ != "ClientDisconnected":
            raise
        setattr(agent, "_ws_disconnected", True)
        setattr(agent, "_ws_disconnect_logged", True)
        print("[WS] disconnected during replay_all; stopping result send")
        return False


def _legacy_control_message(command: dict[str, Any], raw_message: dict[str, Any]) -> dict[str, Any]:
    command_type = str(command.get("type") or "").strip()
    if command_type == "confirmed":
        return {"type": "confirmed"}

    if command_type == "correction":
        control_message: dict[str, Any] = {"type": "correction"}
        correction_text = str(command.get("message") or command.get("answer") or "").strip()
        if correction_text:
            control_message["message"] = correction_text
        run_id = str(command.get("run_id") or "").strip()
        if run_id:
            control_message["run_id"] = run_id
        plan_id = str(command.get("plan_id") or "").strip()
        if plan_id:
            control_message["plan_id"] = plan_id
        target_step_id = str(command.get("step_id") or "").strip()
        if target_step_id:
            control_message["target_step_id"] = target_step_id
        return control_message

    if command_type == "option_selected":
        control_message = {"type": "option_selected"}
        option_value = str(command.get("value") or command.get("answer") or "").strip()
        if option_value:
            control_message["value"] = option_value
            control_message["answer"] = option_value
        run_id = str(command.get("run_id") or "").strip()
        if run_id:
            control_message["run_id"] = run_id
        return control_message

    return dict(raw_message)


def _current_command_state(agent: Any) -> dict[str, Any]:
    state: dict[str, Any] = {}
    phase_getter = getattr(agent, "_current_phase", None)
    if callable(phase_getter):
        phase = str(phase_getter() or "").strip()
        if phase:
            state["phase"] = phase
    if "phase" not in state:
        phase_tracker = getattr(agent, "phase_tracker", None)
        phase_tracker_getter = getattr(phase_tracker, "get_phase", None) if phase_tracker is not None else None
        if callable(phase_tracker_getter):
            phase = str(phase_tracker_getter() or "").strip()
            if phase:
                state["phase"] = phase
    if "phase" not in state:
        agent_phase = str(getattr(agent, "phase", "") or "").strip()
        state["phase"] = agent_phase or "planning"

    run_id_getter = getattr(agent, "_current_run_session_id", None)
    if callable(run_id_getter):
        run_id = str(run_id_getter() or "").strip()
        if run_id:
            state["run_id"] = run_id
    if "run_id" not in state:
        run_session_id = str(getattr(agent, "_run_session_id", "") or "").strip()
        if run_session_id:
            state["run_id"] = run_session_id

    return state


class WSRouter:
    """Maps WebSocket command types to AgentLoop methods."""

    def __init__(self, agent: "AgentLoop", ws: WebSocket, control_queue: asyncio.Queue[dict[str, Any]], run_task_holder: Any) -> None:
        self._agent = agent
        self._ws = ws
        self._control_queue = control_queue
        self._run_task_holder = run_task_holder

    async def dispatch(self, msg: dict[str, Any]) -> bool:
        """Route a parsed WebSocket message to the correct handler.

        Returns False if the connection should be closed, True to continue.
        """
        ws = self._ws
        agent = self._agent
        msg_type = msg.get("type")

        if msg_type in {"run_steps", "llm_run"}:
            steps = msg.get("steps") or []
            run_task = self._run_task_holder.get()
            if run_task and not run_task.done():
                await ws.send_json({"type": "status", "message": "Run already in progress."})
                return True
            new_task = asyncio.create_task(agent.run(steps))
            self._run_task_holder.set(new_task)
            return True

        if msg_type == "save_snapshot":
            current_state = _current_command_state(agent)
            try:
                snapshot = agent._build_spec_snapshot()
                snapshot_event = build_backend_event_envelope(
                    "save_snapshot_result",
                    {"ok": True, "snapshot": snapshot},
                    run_id=current_state.get("run_id"),
                    source="server",
                )
                await ws.send_json(snapshot_event)
            except Exception as exc:  # noqa: BLE001
                error_message = f"Snapshot save failed: {type(exc).__name__}"
                snapshot_event = build_backend_event_envelope(
                    "save_snapshot_result",
                    {"ok": False, "error": error_message},
                    run_id=current_state.get("run_id"),
                    source="server",
                )
                await ws.send_json(snapshot_event)
            return True

        if msg_type == "replay_one":
            step_id = str(msg.get("step_id") or "").strip()
            try:
                result = await agent.replay_one(step_id)
            except Exception as exc:  # noqa: BLE001
                result = {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": step_id,
                    "error": f"Replay failed: {type(exc).__name__}",
                }
            if not await _send_replay_json(ws, agent, result):
                return False
            return True

        if msg_type == "replay_all":
            stop_on_error_value = msg.get("stop_on_error", True)
            if isinstance(stop_on_error_value, bool):
                stop_on_error = stop_on_error_value
            else:
                stop_on_error_text = str(stop_on_error_value or "").strip().lower()
                stop_on_error = stop_on_error_text not in {"false", "0", "no", "off", ""}
            try:
                result = await agent.replay_all(stop_on_error=stop_on_error)
            except WebSocketDisconnect:
                print("[WS] disconnected during replay_all; stopping result send")
                return False
            except RuntimeError as exc:
                if _is_closed_websocket_error(exc):
                    print("[WS] disconnected during replay_all; stopping result send")
                    return False
                raise
            except Exception as exc:  # noqa: BLE001
                if getattr(agent, "_ws_disconnected", False) or exc.__class__.__name__ == "ClientDisconnected":
                    print("[WS] disconnected during replay_all; stopping result send")
                    return False
                fallback_result = {
                    "type": "replay_all_result",
                    "ok": False,
                    "stop_on_error": stop_on_error,
                    "step_ids": [],
                    "replayed_count": 0,
                    "passed_count": 0,
                    "failed_count": 0,
                    "error": f"Replay failed: {type(exc).__name__}",
                }
                if not await _send_replay_json(ws, agent, fallback_result):
                    return False
            else:
                if not getattr(agent, "_replay_all_result_sent", False):
                    if not isinstance(result, dict):
                        result = {
                            "type": "replay_all_result",
                            "ok": False,
                            "stop_on_error": stop_on_error,
                            "step_ids": [],
                            "replayed_count": 0,
                            "passed_count": 0,
                            "failed_count": 0,
                            "error": "Replay failed",
                        }
                    if not await _send_replay_json(ws, agent, result):
                        return False
            return True

        if msg_type in {"confirmed", "correction", "option_selected"}:
            current_state = _current_command_state(agent)
            command, rejection = normalize_frontend_command(msg, current_state=current_state)
            if rejection is not None:
                await ws.send_json(rejection)
                return True
            if command is None:
                await ws.send_json(
                    build_runtime_rejection_payload(
                        "MALFORMED_COMMAND",
                        "Command validation failed.",
                        current_state=current_state,
                        command_id=str(msg.get("command_id") or "").strip() or None,
                        run_id=current_state.get("run_id"),
                        recoverable=False,
                        source="server",
                    )
                )
                return True

            if command.get("source") == "legacy":
                await self._control_queue.put(dict(msg))
            else:
                await self._control_queue.put(_legacy_control_message(command, msg))
            return True

        if msg_type == "arm_picker":
            step_id = str(msg.get("step_id") or "").strip()
            if not step_id:
                await ws.send_json({"type": "error", "message": "arm_picker requires step_id"})
                return True

            async def picker_send(m: dict) -> None:
                await ws.send_json(m)

            await arm_picker(step_id, picker_send)
            await ws.send_json({"type": "status", "message": f"Picker armed for step {step_id}"})
            return True

        if msg_type == "reset":
            agent.llm.reset()
            await ws.send_json({"type": "status", "message": "Session reset."})
            return True

        # Unknown / missing command type
        current_state = _current_command_state(agent)
        if not msg_type:
            await ws.send_json(
                build_runtime_rejection_payload(
                    "MALFORMED_COMMAND",
                    "Command type is required.",
                    current_state=current_state,
                    run_id=current_state.get("run_id"),
                    recoverable=False,
                    source="server",
                )
            )
            return True

        await ws.send_json(
            build_runtime_rejection_payload(
                "COMMAND_NOT_SUPPORTED",
                f"Unsupported message type: {msg_type}",
                current_state=current_state,
                command_id=str(msg.get("command_id") or "").strip() or None,
                run_id=current_state.get("run_id"),
                recoverable=False,
                source="server",
            )
        )
        return True
