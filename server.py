from dotenv import load_dotenv
load_dotenv(override=True)

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from agent import AgentLoop
from browser import arm_picker, launch_browser
from runtime.event_contracts import (
    build_backend_event_envelope,
    build_runtime_rejection_payload,
    normalize_frontend_command,
)

PORT = int(os.getenv("PORT", "8765"))
DISCONNECT_GRACE_SECONDS = 1.5


@dataclass
class WebSocketRunSession:
    agent: AgentLoop
    control_queue: asyncio.Queue[dict[str, Any]]
    ws: WebSocket
    run_task: asyncio.Task[Any] | None = None
    disconnect_grace_task: asyncio.Task[Any] | None = None


def _get_active_run_session() -> WebSocketRunSession | None:
    session = getattr(app.state, "active_run_session", None)
    if isinstance(session, WebSocketRunSession):
        return session
    return None


def _set_active_run_session(session: WebSocketRunSession | None) -> None:
    app.state.active_run_session = session


def _cancel_disconnect_grace(session: WebSocketRunSession) -> None:
    grace_task = session.disconnect_grace_task
    if grace_task is not None and not grace_task.done():
        grace_task.cancel()
    session.disconnect_grace_task = None


async def _expire_stale_run_session(session: WebSocketRunSession) -> None:
    await asyncio.sleep(DISCONNECT_GRACE_SECONDS)
    current_session = _get_active_run_session()
    if current_session is not session:
        return
    run_task = session.run_task
    if run_task is None or run_task.done():
        return
    print("[WS_DISCONNECT_GRACE] grace expired; cancelling stale active run")
    run_task.cancel()
    try:
        await run_task
    except Exception:
        pass
    if _get_active_run_session() is session:
        _set_active_run_session(None)


def _attach_or_create_run_session(ws: WebSocket) -> tuple[WebSocketRunSession, bool]:
    session = _get_active_run_session()
    if session is not None and session.run_task is not None and not session.run_task.done():
        session.ws = ws
        session.agent.ws = ws
        setattr(session.agent, "_ws_disconnected", False)
        setattr(session.agent, "_ws_disconnect_logged", False)
        _cancel_disconnect_grace(session)
        print("[WS_RECONNECT] reattached active run session")
        print("[RUN_TASK_PRESERVED] active run continues after websocket reconnect")
        return session, True

    if session is not None:
        _cancel_disconnect_grace(session)
        _set_active_run_session(None)

    control_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    agent = AgentLoop(ws, control_queue)
    session = WebSocketRunSession(agent=agent, control_queue=control_queue, ws=ws)
    _set_active_run_session(session)
    return session, False


def _is_closed_websocket_error(exc: BaseException) -> bool:
    if isinstance(exc, WebSocketDisconnect):
        return True
    if isinstance(exc, RuntimeError):
        error_text = str(exc)
        return "close message has been sent" in error_text or 'Cannot call "send"' in error_text
    return exc.__class__.__name__ == "ClientDisconnected"


def _current_command_state(session: WebSocketRunSession) -> dict[str, Any]:
    state: dict[str, Any] = {}
    phase_getter = getattr(session.agent, "_current_phase", None)
    if callable(phase_getter):
        phase = str(phase_getter() or "").strip()
        if phase:
            state["phase"] = phase
    if "phase" not in state:
        phase_tracker = getattr(session.agent, "phase_tracker", None)
        phase_tracker_getter = getattr(phase_tracker, "get_phase", None)
        if callable(phase_tracker_getter):
            phase = str(phase_tracker_getter() or "").strip()
            if phase:
                state["phase"] = phase
    if "phase" not in state:
        agent_phase = str(getattr(session.agent, "phase", "") or "").strip()
        state["phase"] = agent_phase or "planning"

    run_id_getter = getattr(session.agent, "_current_run_session_id", None)
    if callable(run_id_getter):
        run_id = str(run_id_getter() or "").strip()
        if run_id:
            state["run_id"] = run_id
    if "run_id" not in state:
        run_session_id = str(getattr(session.agent, "_run_session_id", "") or "").strip()
        if run_session_id:
            state["run_id"] = run_session_id

    return state


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


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or not key.startswith("sk-"):
        raise RuntimeError("OPENAI_API_KEY missing or invalid in .env")
    print("[startup] OPENAI_API_KEY loaded: yes source: repo .env")
    print(f"[startup] PORT={PORT}")
    await launch_browser()
    yield


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    await ws.send_json({"type": "status", "message": "Browser launched. Ready."})

    session, _reattached = _attach_or_create_run_session(ws)

    async def picker_send(msg: dict) -> None:
        await ws.send_json(msg)

    try:
        while True:
            msg = await ws.receive_json()
            msg_type = msg.get("type")

            if msg_type in {"run_steps", "llm_run"}:
                steps = msg.get("steps") or []
                if session.run_task and not session.run_task.done():
                    await ws.send_json({"type": "status", "message": "Run already in progress."})
                    continue
                run_task = asyncio.create_task(session.agent.run(steps))
                session.run_task = run_task

                def _clear_session_when_done(task: asyncio.Task[Any]) -> None:
                    if session.run_task is task:
                        session.run_task = None
                        _cancel_disconnect_grace(session)
                        if _get_active_run_session() is session:
                            _set_active_run_session(None)

                run_task.add_done_callback(_clear_session_when_done)
                continue

            if msg_type == "save_snapshot":
                try:
                    snapshot = session.agent._build_spec_snapshot()
                    snapshot_event = build_backend_event_envelope(
                        "save_snapshot_result",
                        {
                            "ok": True,
                            "snapshot": snapshot,
                        },
                        run_id=_current_command_state(session).get("run_id"),
                        source="server",
                    )
                    await ws.send_json(snapshot_event)
                except Exception as exc:  # noqa: BLE001
                    error_message = f"Snapshot save failed: {type(exc).__name__}"
                    snapshot_event = build_backend_event_envelope(
                        "save_snapshot_result",
                        {
                            "ok": False,
                            "error": error_message,
                        },
                        run_id=_current_command_state(session).get("run_id"),
                        source="server",
                    )
                    await ws.send_json(snapshot_event)
                continue

            if msg_type == "replay_one":
                step_id = str(msg.get("step_id") or "").strip()
                try:
                    result = await session.agent.replay_one(step_id)
                except Exception as exc:  # noqa: BLE001
                    result = {
                        "type": "replay_one_result",
                        "ok": False,
                        "step_id": step_id,
                        "error": f"Replay failed: {type(exc).__name__}",
                    }
                if not await _send_replay_json(ws, session.agent, result):
                    break
                continue

            if msg_type == "replay_all":
                stop_on_error_value = msg.get("stop_on_error", True)
                if isinstance(stop_on_error_value, bool):
                    stop_on_error = stop_on_error_value
                else:
                    stop_on_error_text = str(stop_on_error_value or "").strip().lower()
                    stop_on_error = stop_on_error_text not in {"false", "0", "no", "off", ""}
                try:
                    result = await session.agent.replay_all(stop_on_error=stop_on_error)
                except WebSocketDisconnect:
                    print("[WS] disconnected during replay_all; stopping result send")
                    break
                except RuntimeError as exc:
                    if _is_closed_websocket_error(exc):
                        print("[WS] disconnected during replay_all; stopping result send")
                        break
                    raise
                except Exception as exc:  # noqa: BLE001
                    if getattr(session.agent, "_ws_disconnected", False) or exc.__class__.__name__ == "ClientDisconnected":
                        print("[WS] disconnected during replay_all; stopping result send")
                        break
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
                    if not await _send_replay_json(ws, session.agent, fallback_result):
                        break
                else:
                    if not getattr(session.agent, "_replay_all_result_sent", False):
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
                        if not await _send_replay_json(ws, session.agent, result):
                            break
                continue

            if msg_type in {"confirmed", "correction", "option_selected"}:
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
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
                    continue

                if command.get("source") == "legacy":
                    await session.control_queue.put(dict(msg))
                else:
                    await session.control_queue.put(_legacy_control_message(command, msg))
                continue

            if msg_type == "arm_picker":
                step_id = str(msg.get("step_id") or "").strip()
                if not step_id:
                    await ws.send_json({"type": "error", "message": "arm_picker requires step_id"})
                    continue
                await arm_picker(step_id, picker_send)
                await ws.send_json({"type": "status", "message": f"Picker armed for step {step_id}"})
                continue

            if msg_type == "reset":
                session.agent.llm.reset()
                await ws.send_json({"type": "status", "message": "Session reset."})
                continue

            current_state = _current_command_state(session)
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
                continue

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
    except WebSocketDisconnect:
        if session.run_task and not session.run_task.done():
            print("[WS_DISCONNECT_GRACE] active run disconnected; awaiting reconnect")
            if session.disconnect_grace_task is None or session.disconnect_grace_task.done():
                session.disconnect_grace_task = asyncio.create_task(_expire_stale_run_session(session))
        elif _get_active_run_session() is session:
            _set_active_run_session(None)


if __name__ == "__main__":
    import uvicorn

    print(f"[main] Starting server on 0.0.0.0:{int(os.getenv('PORT', 8765))}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8765)))
