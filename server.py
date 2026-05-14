from dotenv import load_dotenv
# override=False so shell exports (scripts/launch.sh) win over .env.
load_dotenv(override=False)

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
    build_load_result_event,
    build_runtime_rejection_payload,
    build_save_result_event,
    build_session_state_event,
    build_stop_run_result_event,
    build_typed_ready_envelope,
    normalize_frontend_command,
)
from runtime.session_store import SessionSpec, load_session_from_file, save_session_to_file

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


def _build_session_state_event(session: WebSocketRunSession) -> dict[str, Any] | None:
    payload_builder = getattr(session.agent, "_build_session_state_payload", None)
    if not callable(payload_builder):
        return None

    payload = payload_builder()
    if not isinstance(payload, dict):
        return None

    return build_session_state_event(payload, source="server")


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


from runtime.log import log as _log, log_front as _log_front, log_error as _log_error  # noqa: E402
from fastapi import Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

# Frontend may be served from a separate origin (e.g. the static fixture server
# on :8000) while it POSTs logs to this backend on :8765. Allow all origins on
# dev — this server is loopback-only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/log")
async def api_log(request: Request) -> dict[str, bool]:
    """Frontend log ingest. Frontend POSTs one log entry; backend re-emits to
    stdout so /tmp/aw-launch.log is the unified trace."""
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001
        _log_error("LOG_INGEST", "could not parse json", exc=exc)
        return {"ok": False}
    if isinstance(body, list):
        for item in body:
            _log_front(item if isinstance(item, dict) else {"category": "FRONT", "raw": item})
    elif isinstance(body, dict):
        _log_front(body)
    else:
        _log_front({"category": "FRONT", "raw": body})
    return {"ok": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    session, _reattached = _attach_or_create_run_session(ws)

    session_state_event = _build_session_state_event(session)
    if session_state_event is not None:
        await ws.send_json(session_state_event)

    # S7-0105: emit typed ready envelope — PRD-04-BE-006
    _session_id = str(getattr(session.agent, "_current_run_session_id", lambda: "")() or "").strip() or "session"
    _workspace = os.getenv("AUTOWORKBENCH_WORKSPACE", os.getcwd())
    _ready_event = build_typed_ready_envelope(
        session_id=_session_id,
        workspace=_workspace,
        mode="complete",
        url=str(getattr(session.agent, "page_url", None) or ""),
        backend_ready=True,
        browser_ready=True,
    )
    await ws.send_json(_ready_event)

    async def picker_send(msg: dict) -> None:
        await ws.send_json(msg)

    try:
        while True:
            msg = await ws.receive_json()
            msg_type = msg.get("type")
            print(f"[WS_RECV] type={msg_type}", flush=True)

            if msg_type in {"run_steps", "llm_run"}:
                steps = msg.get("steps") or []
                print(f"[RUN_STEPS] n={len(steps)}", flush=True)
                if session.run_task and not session.run_task.done():
                    await ws.send_json({"type": "status", "message": "Run already in progress."})
                    continue
                print("[AGENT_RUN] starting agent.run task", flush=True)
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

            # S7-0107: stop_run command handler — PRD-04-CMD-001
            if msg_type == "stop_run":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _active_run_id = current_state.get("run_id") or ""
                if _cmd_run_id and _cmd_run_id != _active_run_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "STALE_RUN_ID",
                            f"run_id {_cmd_run_id!r} does not match active run.",
                            current_state=current_state,
                            run_id=_active_run_id or None,
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                if session.run_task and not session.run_task.done():
                    session.run_task.cancel()
                _stop_event = build_stop_run_result_event(
                    run_id=_active_run_id or _cmd_run_id or "unknown",
                    status="stopped",
                    reason="user_requested",
                )
                await ws.send_json(_stop_event)
                continue

            # S7-0108: skip_step command handler — PRD-04-CMD-002
            if msg_type == "skip_step":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _active_run_id = current_state.get("run_id") or ""
                if _cmd_run_id and _cmd_run_id != _active_run_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "STALE_RUN_ID",
                            f"run_id {_cmd_run_id!r} does not match active run.",
                            current_state=current_state,
                            run_id=_active_run_id or None,
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                await session.control_queue.put({"type": "skip_step", "run_id": _active_run_id, "step_id": str(msg.get("step_id") or "").strip()})
                continue

            # S7-0109: save_session command handler — PRD-04-CMD-003
            if msg_type == "save_session":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _run_id = current_state.get("run_id") or ""
                try:
                    _spec_builder = getattr(session.agent, "_build_spec_snapshot", None)
                    _raw_spec = _spec_builder() if callable(_spec_builder) else {}
                    _spec = SessionSpec(
                        title=str(_raw_spec.get("title") or msg.get("name") or "session"),
                        steps=list(_raw_spec.get("steps") or []),
                        page_url=str(_raw_spec.get("page_url") or getattr(session.agent, "page_url", "") or ""),
                        recorded_steps=list(_raw_spec.get("recorded_steps") or []),
                        code_preview=_raw_spec.get("code_preview"),
                        session_id=_run_id or None,
                        metadata=dict(_raw_spec.get("metadata") or {}),
                    )
                    _save_path, _save_name = save_session_to_file(
                        _spec,
                        name=str(msg.get("name") or "").strip() or None,
                    )
                    _save_event = build_save_result_event(
                        path=_save_path,
                        name=_save_name,
                        session_id=_run_id or _save_name,
                        step_count=len(_spec.steps),
                    )
                    await ws.send_json(_save_event)
                except Exception as exc:  # noqa: BLE001
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "SAVE_FAILED",
                            f"save_session failed: {type(exc).__name__}: {exc}",
                            current_state=current_state,
                            run_id=_run_id or None,
                            recoverable=False,
                            source="server",
                        )
                    )
                continue

            # S7-0109: load_session command handler — PRD-04-CMD-004
            if msg_type == "load_session":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _run_id = current_state.get("run_id") or ""
                _load_path = str(msg.get("path") or "").strip()
                if not _load_path:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MISSING_PATH",
                            "load_session requires 'path' field.",
                            current_state=current_state,
                            run_id=_run_id or None,
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                try:
                    _loaded_spec = load_session_from_file(_load_path)
                    _load_event = build_load_result_event(
                        path=_load_path,
                        name=str(_loaded_spec.title or ""),
                        session_id=str(_loaded_spec.session_id or _run_id or ""),
                        step_count=len(_loaded_spec.steps),
                        snapshot_valid=True,
                    )
                    await ws.send_json(_load_event)
                except (FileNotFoundError, ValueError, TypeError) as exc:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "LOAD_FAILED",
                            f"load_session failed: {type(exc).__name__}: {exc}",
                            current_state=current_state,
                            run_id=_run_id or None,
                            recoverable=False,
                            source="server",
                        )
                    )
                continue

            # S7-0104: permission_decision command handler — PRD-04-CMD-005
            if msg_type == "permission_decision":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _active_run_id = current_state.get("run_id") or ""
                if _cmd_run_id and _cmd_run_id != _active_run_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "STALE_RUN_ID",
                            f"run_id {_cmd_run_id!r} does not match active run.",
                            current_state=current_state,
                            run_id=_active_run_id or None,
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                await session.control_queue.put(dict(msg))
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
