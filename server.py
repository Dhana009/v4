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
    build_agent_settings_event,
    build_api_key_required_event,
    build_endpoint_registry_event,
    build_no_browser_event,
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


# Runtime degradation state — populated by lifespan, read by WS connect to
# emit the matching state-card events (E2/B2) instead of crashing the server.
_BOOT_STATE: dict[str, object] = {
    "api_key_ok": False,
    "api_key_reason": None,  # "missing" | "invalid" | None
    "browser_ok": False,
    "browser_error": None,
    "stub_mode": False,
}


def _classify_api_key() -> tuple[bool, str | None]:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return False, "missing"
    if not key.startswith("sk-"):
        return False, "invalid"
    return True, None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Graceful boot: never crash on missing env / browser failure.

    Sprint-7 / F1 — server must boot in both modes:
      • Real: real OPENAI_API_KEY + Playwright browser.
      • Stub: AUTOWORKBENCH_STUB_MODE=1 → skip key + browser launch; WS
        clients receive api_key_required + no_browser state-card events.

    On any boot failure we record the cause in `_BOOT_STATE` and emit the
    matching event from the WS handler on connect (E2 / B2).
    """
    _BOOT_STATE["stub_mode"] = os.getenv("AUTOWORKBENCH_STUB_MODE", "").lower() in (
        "1",
        "true",
        "yes",
    )

    api_ok, api_reason = _classify_api_key()
    _BOOT_STATE["api_key_ok"] = api_ok
    _BOOT_STATE["api_key_reason"] = api_reason
    if api_ok:
        print("[startup] OPENAI_API_KEY loaded: yes source: repo .env", flush=True)
    elif _BOOT_STATE["stub_mode"]:
        print(
            f"[startup] OPENAI_API_KEY {api_reason or 'missing'} — stub mode active",
            flush=True,
        )
    else:
        print(
            f"[startup] OPENAI_API_KEY {api_reason or 'missing'} — frontend will "
            "show api_key_required; LLM calls will refuse until a key is set",
            flush=True,
        )

    print(f"[startup] PORT={PORT}", flush=True)

    if _BOOT_STATE["stub_mode"]:
        print("[startup] AUTOWORKBENCH_STUB_MODE=1 — skipping browser launch", flush=True)
    else:
        try:
            await launch_browser()
            _BOOT_STATE["browser_ok"] = True
        except Exception as exc:  # noqa: BLE001
            _BOOT_STATE["browser_ok"] = False
            _BOOT_STATE["browser_error"] = str(exc) or type(exc).__name__
            print(
                f"[startup] browser launch failed: {exc!r} — frontend will show "
                "no_browser; runs blocked until recovered",
                flush=True,
            )

    yield


app = FastAPI(lifespan=lifespan)


from runtime.log import log as _log, log_front as _log_front, log_error as _log_error  # noqa: E402
from fastapi import Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

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

    # E1 / B1 — emit agent_settings on every WS connect so the v4 popover
    # renders real backend-driven rows instead of an honest empty state.
    # Sprint 7 ships in read-only mode (no set_agent_enabled command yet).
    await ws.send_json(build_agent_settings_event())

    # F1 / E2 — degraded-boot advisories. The lifespan never crashes on
    # missing key or browser failure; instead it records the cause in
    # _BOOT_STATE and we emit the matching typed state-card event here
    # so the frontend can render the honest empty state.
    if not _BOOT_STATE.get("api_key_ok"):
        await ws.send_json(
            build_api_key_required_event(
                provider="openai",
                reason=str(_BOOT_STATE.get("api_key_reason") or "missing"),
                missing_config_keys=["OPENAI_API_KEY"],
                message=(
                    "Set OPENAI_API_KEY in your environment (or .env). LLM mode "
                    "is paused until a valid key is present."
                ),
                setup_hint={"url": "https://platform.openai.com/api-keys"},
            )
        )
    if not _BOOT_STATE.get("browser_ok") and not _BOOT_STATE.get("stub_mode"):
        await ws.send_json(
            build_no_browser_event(
                reason="not_launched",
                recoverable=True,
                message=(
                    "Backend booted but the Playwright browser failed to launch. "
                    "Restart the backend service or run `playwright install` to "
                    "recover."
                ),
                suggested_action="relaunch_browser",
            )
        )

    # E3 / B5 — emit endpoint_registry on every WS connect. Sprint 7 ships
    # a single-entry registry pointing at the current local backend; the
    # CardOffline "Switch endpoint" button stays honestly disabled until
    # an additional endpoint is registered. The cmd `switch_endpoint`
    # accepts an ``endpoint_id`` only — never a raw URL — so no SSRF /
    # open-redirect risk exists even if the frontend is compromised.
    _local_endpoint_id = "local"
    _local_endpoint_url = f"ws://127.0.0.1:{PORT}/ws"
    await ws.send_json(
        build_endpoint_registry_event(
            active_id=_local_endpoint_id,
            entries=[
                {
                    "id": _local_endpoint_id,
                    "label": "Local",
                    "base_url": _local_endpoint_url,
                    "kind": "local",
                }
            ],
        )
    )

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
                    # Contract: when a new llm_run arrives while a run_task is already live,
                    # emit a typed run_rejected envelope so the frontend can surface a toast.
                    # Fields: reason (machine key), active_run_id (nullable), message (human text).
                    await ws.send_json({
                        "type": "run_rejected",
                        "payload": {
                            "reason": "run_already_in_progress",
                            "active_run_id": getattr(session.agent, "current_run_id", None),
                            "message": "Resolve the current clarification or cancel before starting a new run.",
                        },
                    })
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

            if msg_type == "export_code":
                # D-103: write generated spec to workspace file; emit export_code_result.
                # Backend owns the file-write; frontend never writes the filesystem.
                code_str = str(msg.get("code") or "").strip()
                explicit_path = str(msg.get("path") or "").strip() or None
                if not code_str:
                    export_event = build_backend_event_envelope(
                        "export_code_result",
                        {"ok": False, "error": "code is required and must be a non-empty string"},
                        source="server",
                    )
                else:
                    _workspace = os.getenv("AUTOWORKBENCH_WORKSPACE", os.getcwd())
                    _workspace_resolved = os.path.realpath(_workspace)
                    _output_dir = os.path.join(_workspace, "autoworkbench-output")
                    if explicit_path:
                        # D-103 security: explicit_path is user-supplied; resolve and
                        # require containment in the workspace to prevent path traversal.
                        if os.path.isabs(explicit_path):
                            _candidate = explicit_path
                        else:
                            _candidate = os.path.join(_workspace, explicit_path)
                        target_path = os.path.realpath(_candidate)
                    else:
                        os.makedirs(_output_dir, exist_ok=True)
                        target_path = os.path.realpath(
                            os.path.join(_output_dir, "generated.spec.ts")
                        )
                    _contained = (
                        target_path == _workspace_resolved
                        or target_path.startswith(_workspace_resolved + os.sep)
                    )
                    if not _contained:
                        export_event = build_backend_event_envelope(
                            "export_code_result",
                            {
                                "ok": False,
                                "error": "path must be inside the workspace",
                            },
                            source="server",
                        )
                    else:
                        try:
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with open(target_path, "w", encoding="utf-8") as _f:
                                _f.write(code_str)
                            export_event = build_backend_event_envelope(
                                "export_code_result",
                                {"ok": True, "path": target_path},
                                source="server",
                            )
                        except OSError as _exc:
                            export_event = build_backend_event_envelope(
                                "export_code_result",
                                {"ok": False, "error": str(_exc)},
                                source="server",
                            )
                await ws.send_json(export_event)
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

            # T-13: add_api_key command — accepts an OpenAI key in the
            # message body, writes it to the process environment so the
            # next LLMClient() ctor succeeds, and flips _BOOT_STATE.
            # The key is NEVER echoed back over the wire; the ack only
            # confirms acceptance and that the boot state was updated.
            if msg_type == "add_api_key":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection); continue
                _key = str(msg.get("key") or "").strip()
                _provider = str(msg.get("provider") or "openai").strip().lower() or "openai"
                if not _key or not _key.startswith("sk-"):
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "INVALID_API_KEY",
                            "add_api_key requires a non-empty key starting with 'sk-'.",
                            current_state=current_state,
                            recoverable=True,
                            source="server",
                        )
                    )
                    continue
                # Write to process env. Persist to .env is intentionally
                # out of scope for this slice — restart picks up env only.
                os.environ["OPENAI_API_KEY"] = _key
                _BOOT_STATE["api_key_ok"] = True
                _BOOT_STATE["api_key_reason"] = None
                await ws.send_json(
                    build_backend_event_envelope(
                        "add_api_key_acknowledged",
                        {"provider": _provider, "status": "accepted", "applied": True},
                        source="server",
                    )
                )
                continue

            # T-13: use_workspace_key command — instructs the backend to
            # pick up the shared workspace key (e.g. from a settings file
            # outside the per-user env). Ack only for now; the resolver
            # lives in a follow-up since it needs a workspace config
            # schema decision (open ambiguity in integration map §10).
            if msg_type == "use_workspace_key":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection); continue
                await session.control_queue.put({"type": "use_workspace_key"})
                await ws.send_json(
                    build_backend_event_envelope(
                        "use_workspace_key_acknowledged",
                        {"status": "accepted", "applied": False},
                        source="server",
                    )
                )
                continue

            # T-12: launch_chromium command — calls browser.launch_browser
            # so the FE can recover from a no-browser state without a
            # backend restart. Emits browser_ready on success or a typed
            # error envelope on failure.
            if msg_type == "launch_chromium":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection); continue
                try:
                    await launch_browser()
                    _BOOT_STATE["browser_ok"] = True
                    _BOOT_STATE["browser_error"] = None
                    await ws.send_json(
                        build_backend_event_envelope(
                            "launch_chromium_acknowledged",
                            {"status": "accepted", "applied": True},
                            source="server",
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    _BOOT_STATE["browser_ok"] = False
                    _BOOT_STATE["browser_error"] = str(exc) or type(exc).__name__
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "BROWSER_LAUNCH_FAILED",
                            f"launch_browser failed: {type(exc).__name__}",
                            current_state=current_state,
                            recoverable=True,
                            source="server",
                        )
                    )
                continue

            # T-12: attach_existing_tab — user supplies a URL of a tab
            # to attach to. Acked only for now; the actual CDP attach
            # is a follow-up. URL is echoed in the ack so the UI can
            # surface it; never executed by the server.
            if msg_type == "attach_existing_tab":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection); continue
                _url = str(msg.get("url") or "").strip()
                await session.control_queue.put({
                    "type": "attach_existing_tab",
                    "url": _url,
                })
                await ws.send_json(
                    build_backend_event_envelope(
                        "attach_existing_tab_acknowledged",
                        {"url": _url, "status": "accepted", "applied": False},
                        source="server",
                    )
                )
                continue

            # T-12: keep_plan_as_draft — user defers running; backend just
            # acks and the FE state machine returns to idle/draft.
            if msg_type == "keep_plan_as_draft":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection); continue
                await session.control_queue.put({"type": "keep_plan_as_draft"})
                await ws.send_json(
                    build_backend_event_envelope(
                        "keep_plan_as_draft_acknowledged",
                        {"status": "accepted"},
                        source="server",
                    )
                )
                continue

            # T-11: retry_as_is command — re-run the failed step without
            # any plan correction. Forward onto control_queue + ack.
            if msg_type == "retry_as_is":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection); continue
                _step_id = str(msg.get("step_id") or "").strip()
                _run_id = current_state.get("run_id") or str(msg.get("run_id") or "").strip() or ""
                await session.control_queue.put({
                    "type": "retry_as_is",
                    "step_id": _step_id,
                    "run_id": _run_id,
                })
                await ws.send_json(
                    build_backend_event_envelope(
                        "retry_as_is_acknowledged",
                        {"step_id": _step_id, "run_id": _run_id, "status": "accepted"},
                        source="server",
                        run_id=_run_id or None,
                    )
                )
                continue

            # T-5: download_trace command handler. Acks the request without
            # actually bundling — the trace pipeline is wired in a later
            # task. The contract lands now so the FE has a typed surface
            # to integrate against.
            if msg_type == "download_trace":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _run_id = current_state.get("run_id") or str(msg.get("run_id") or "").strip() or ""
                await ws.send_json(
                    build_backend_event_envelope(
                        "download_trace_acknowledged",
                        {"run_id": _run_id, "status": "queued", "applied": False},
                        source="server",
                        run_id=_run_id or None,
                    )
                )
                continue

            # T-4: pause / resume command handlers.
            # Minimal surface for the FE buttons; the agent loop will start
            # honouring `paused` flag in a follow-up task. For now we ack on
            # the wire so the FE has a typed contract to integrate against,
            # forward the command onto the agent control_queue so a future
            # loop tick can react, and emit a typed envelope for the trace.
            if msg_type in {"pause", "resume"}:
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _active_run_id = current_state.get("run_id") or ""
                if _cmd_run_id and _active_run_id and _cmd_run_id != _active_run_id:
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
                await session.control_queue.put({
                    "type": msg_type,
                    "run_id": _active_run_id or _cmd_run_id or "",
                })
                ack_event = build_backend_event_envelope(
                    f"{msg_type}_acknowledged",
                    {
                        "run_id": _active_run_id or _cmd_run_id or "",
                        "status": "queued",
                    },
                    source="server",
                )
                await ws.send_json(ack_event)
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

            # D-101: change_precondition command handler — PRD-05-Replay-Precondition-Guard-v1
            if msg_type == "change_precondition":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _step_id = str(msg.get("step_id") or "").strip()
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _expected_url = str(msg.get("expected_url") or "").strip()
                _new_precondition = msg.get("new_precondition")
                if not _step_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MALFORMED_COMMAND",
                            "change_precondition requires step_id.",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                if not _cmd_run_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MALFORMED_COMMAND",
                            "change_precondition requires run_id.",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                if not _expected_url and not _new_precondition:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MALFORMED_COMMAND",
                            "change_precondition requires expected_url or new_precondition.",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                # Route through correction pipeline (precondition change is structurally
                # a plan correction). Package as typed correction envelope.
                _correction_envelope = {
                    "type": "correction",
                    "step_id": _step_id,
                    "run_id": _cmd_run_id,
                    "expected_url": _expected_url,
                    "message": f"Update precondition for step {_step_id}: expected_url={_expected_url}",
                    "source": "frontend",
                }
                await session.control_queue.put(_correction_envelope)
                _precondition_updated_event = build_backend_event_envelope(
                    "step_precondition_updated",
                    {
                        "step_id": _step_id,
                        "new_precondition": _new_precondition or {"expected_url": _expected_url, "status": "pending"},
                    },
                    source="server",
                    run_id=_cmd_run_id or None,
                )
                await ws.send_json(_precondition_updated_event)
                continue

            # D-101: navigate_to_expected command handler — PRD-05-Replay-Precondition-Guard-v1
            if msg_type == "navigate_to_expected":
                current_state = _current_command_state(session)
                command, rejection = normalize_frontend_command(msg, current_state=current_state)
                if rejection is not None:
                    await ws.send_json(rejection)
                    continue
                _step_id = str(msg.get("step_id") or "").strip()
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _active_run_id = current_state.get("run_id") or ""
                if not _step_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MALFORMED_COMMAND",
                            "navigate_to_expected requires step_id.",
                            current_state=current_state,
                            run_id=_active_run_id or None,
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                if not _cmd_run_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MALFORMED_COMMAND",
                            "navigate_to_expected requires run_id.",
                            current_state=current_state,
                            run_id=_active_run_id or None,
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                # Stale run_id check (navigation must target the active run)
                if _cmd_run_id and _active_run_id and _cmd_run_id != _active_run_id:
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
                # Emit acknowledged event and queue for agent replay-precondition flow.
                # Navigation permission policy: navigate_to_expected is generally allowed
                # (non-destructive URL restoration per Replay Precondition Guard v1).
                _nav_ack_event = build_backend_event_envelope(
                    "navigate_to_expected_acknowledged",
                    {
                        "step_id": _step_id,
                        "run_id": _cmd_run_id or _active_run_id or "",
                        "status": "accepted",
                    },
                    source="server",
                    run_id=_cmd_run_id or _active_run_id or None,
                )
                await ws.send_json(_nav_ack_event)
                # Delegate navigation intent to the agent's replay-precondition flow
                # via the control queue.
                await session.control_queue.put({
                    "type": "navigate_to_expected",
                    "step_id": _step_id,
                    "run_id": _cmd_run_id or _active_run_id,
                })
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

            # D-101: improve_locator command handler
            # view_candidates maps to same path per spec Sub-area A note.
            if msg_type in {"improve_locator", "view_candidates"}:
                current_state = _current_command_state(session)
                _step_id = str(msg.get("step_id") or "").strip()
                if not _step_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MISSING_STEP_ID",
                            f"{msg_type} requires 'step_id' field.",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _active_run_id = current_state.get("run_id") or ""
                if _cmd_run_id and _active_run_id and _cmd_run_id != _active_run_id:
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
                # T-10: route the typed intent onto the agent control_queue
                # so a follow-up can wire a real locator re-search. The ack
                # carries status="accepted" since the request has been
                # delivered into the agent loop (was "queued" before).
                await session.control_queue.put({
                    "type": msg_type,
                    "step_id": _step_id,
                    "run_id": _cmd_run_id or _active_run_id or "",
                })
                _ack = build_backend_event_envelope(
                    "improve_locator_acknowledged",
                    {"step_id": _step_id, "status": "accepted"},
                    source="server",
                )
                await ws.send_json(_ack)
                continue

            # D-101: change_locator_scope command handler
            if msg_type == "change_locator_scope":
                current_state = _current_command_state(session)
                _step_id = str(msg.get("step_id") or "").strip()
                if not _step_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MISSING_STEP_ID",
                            "change_locator_scope requires 'step_id' field.",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                _scope = str(msg.get("scope") or "").strip()
                if not _scope:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MISSING_SCOPE",
                            "change_locator_scope requires 'scope' field (broader|narrower|free-text).",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _active_run_id = current_state.get("run_id") or ""
                if _cmd_run_id and _active_run_id and _cmd_run_id != _active_run_id:
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
                # T-10: route onto control_queue so a follow-up can teach
                # the agent loop to widen / narrow the locator scope.
                await session.control_queue.put({
                    "type": "change_locator_scope",
                    "step_id": _step_id,
                    "scope": _scope,
                    "run_id": _cmd_run_id or _active_run_id or "",
                })
                _ack = build_backend_event_envelope(
                    "change_locator_scope_acknowledged",
                    {"step_id": _step_id, "scope": _scope, "status": "accepted"},
                    source="server",
                )
                await ws.send_json(_ack)
                continue

            # E3 / B3 — highlight a single locator candidate.
            # Acknowledge only — Sprint 7 has no browser-side highlight
            # helper exposed through the runtime, so the cmd is a typed
            # fire-and-forget that proves the wiring without lying about
            # an effect that does not happen yet.
            if msg_type == "highlight_locator":
                current_state = _current_command_state(session)
                _candidate_id = str(msg.get("candidate_id") or "").strip()
                if not _candidate_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MISSING_CANDIDATE_ID",
                            "highlight_locator requires 'candidate_id' field.",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                _duration_ms = msg.get("duration_ms")
                try:
                    _duration_ms = int(_duration_ms) if _duration_ms is not None else 1500
                except (TypeError, ValueError):
                    _duration_ms = 1500
                _duration_ms = max(0, min(_duration_ms, 5000))
                # T-10: route through control_queue so a follow-up can hook
                # into the live browser overlay. Status flips to "accepted"
                # to reflect that the agent has the intent now.
                await session.control_queue.put({
                    "type": "highlight_locator",
                    "candidate_id": _candidate_id,
                    "duration_ms": _duration_ms,
                })
                await ws.send_json(
                    build_backend_event_envelope(
                        "locator_highlight_acknowledged",
                        {
                            "candidate_id": _candidate_id,
                            "duration_ms": _duration_ms,
                            "applied": False,
                            "status": "accepted",
                        },
                        source="server",
                    )
                )
                continue

            # E3 / B5 — endpoint switch. Sprint 7 advertises a single-entry
            # registry (current local), so any switch request that names a
            # non-active endpoint is rejected here without ever touching a
            # URL the frontend supplied.
            if msg_type == "switch_endpoint":
                current_state = _current_command_state(session)
                _endpoint_id = str(msg.get("endpoint_id") or "").strip()
                if not _endpoint_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "MISSING_ENDPOINT_ID",
                            "switch_endpoint requires 'endpoint_id' field.",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=False,
                            source="server",
                        )
                    )
                    continue
                if _endpoint_id != _local_endpoint_id:
                    await ws.send_json(
                        build_runtime_rejection_payload(
                            "ENDPOINT_UNKNOWN",
                            f"endpoint_id {_endpoint_id!r} is not in the registry.",
                            current_state=current_state,
                            run_id=current_state.get("run_id"),
                            recoverable=True,
                            source="server",
                        )
                    )
                    continue
                # Asking to switch to the already-active endpoint is a no-op
                # ack so the frontend can rely on a typed response.
                await ws.send_json(
                    build_backend_event_envelope(
                        "switch_endpoint_acknowledged",
                        {"endpoint_id": _endpoint_id, "status": "already_active"},
                        source="server",
                    )
                )
                continue

            # Wire 1: apply_plan_edit — P0 item 4
            # Routes FE plan-edit ops onto the control_queue so agent.py's
            # _wait_for_plan_confirmation loop can handle them.
            if msg_type == "apply_plan_edit":
                current_state = _current_command_state(session)
                _cmd_run_id = str(msg.get("run_id") or "").strip()
                _active_run_id = current_state.get("run_id") or ""
                await session.control_queue.put({
                    "type": "apply_plan_edit",
                    "run_id": _cmd_run_id or _active_run_id or "",
                    "edit_op": msg.get("edit_op"),
                    "payload": msg,
                })
                await ws.send_json(
                    build_backend_event_envelope(
                        "apply_plan_edit_acknowledged",
                        {"run_id": _cmd_run_id or _active_run_id or "", "status": "accepted"},
                        source="server",
                        run_id=_cmd_run_id or _active_run_id or None,
                    )
                )
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


# Serve the v4 frontend (shadow-DOM mounted React + Babel runtime) from the
# same origin as /ws so the browser does not need CORS to read styles.css or
# the JSX files. Mounted last so /api/log and /ws keep priority.
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    print(f"[main] Starting server on 0.0.0.0:{int(os.getenv('PORT', 8765))}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8765)))
