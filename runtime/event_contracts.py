from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

BACKEND_EVENT_SCHEMA_VERSION = "autoworkbench.event.v1"
FRONTEND_COMMAND_SCHEMA_VERSION = "autoworkbench.command.v1"
RUNTIME_REJECTION_SCHEMA_VERSION = "autoworkbench.rejection.v1"

SUPPORTED_FRONTEND_COMMAND_TYPES = {
    "confirmed",
    "correction",
    "option_selected",
    # Sprint 7 Cluster 1 — new command types
    "stop_run",
    "skip_step",
    "save_session",
    "load_session",
    "permission_decision",
    # D-103 — export_code: save generated spec to workspace file
    "export_code",
    # D-101 — locator cluster commands
    "improve_locator",
    "view_candidates",
    "change_locator_scope",
    # D-101 — state-cluster commands: precondition + navigation
    "change_precondition",
    "navigate_to_expected",
}


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _json_safe_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=True))


def _coerce_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def _default_emitted_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_backend_event_envelope(
    event_type: str,
    payload: Mapping[str, Any] | None = None,
    *,
    schema_version: str = BACKEND_EVENT_SCHEMA_VERSION,
    run_id: str | None = None,
    event_id: str | None = None,
    emitted_at: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    event_name = _coerce_text(event_type)
    if not event_name:
        raise ValueError("event_type is required")

    payload_data = _json_safe_copy(_coerce_mapping(payload))
    envelope: dict[str, Any] = {
        "type": event_name,
        "schema_version": _coerce_text(schema_version) or BACKEND_EVENT_SCHEMA_VERSION,
        "payload": payload_data,
    }

    if run_id:
        envelope["run_id"] = _coerce_text(run_id)
    if event_id:
        envelope["event_id"] = _coerce_text(event_id)
    envelope["emitted_at"] = _coerce_text(emitted_at) or _default_emitted_at()
    if source:
        envelope["source"] = _coerce_text(source)

    if isinstance(payload_data, dict):
        for key, value in payload_data.items():
            if key in envelope:
                continue
            envelope[key] = _json_safe_copy(value)

    return envelope


def build_frontend_command_envelope(
    command_type: str,
    payload: Mapping[str, Any] | None = None,
    *,
    command_id: str,
    source: str = "frontend",
    run_id: str | None = None,
    schema_version: str = FRONTEND_COMMAND_SCHEMA_VERSION,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    command_name = _coerce_text(command_type)
    if not command_name:
        raise ValueError("command_type is required")

    command_identifier = _coerce_text(command_id)
    if not command_identifier:
        raise ValueError("command_id is required")

    payload_data = _json_safe_copy(_coerce_mapping(payload))
    envelope: dict[str, Any] = {
        "type": command_name,
        "schema_version": _coerce_text(schema_version) or FRONTEND_COMMAND_SCHEMA_VERSION,
        "command_id": command_identifier,
        "source": _coerce_text(source) or "frontend",
        "payload": payload_data,
    }

    if run_id:
        envelope["run_id"] = _coerce_text(run_id)
    envelope["emitted_at"] = _coerce_text(emitted_at) or _default_emitted_at()

    if isinstance(payload_data, dict):
        for key, value in payload_data.items():
            if key in envelope:
                continue
            envelope[key] = _json_safe_copy(value)

    return envelope


def build_runtime_rejection_payload(
    rejection_code: str,
    message: str,
    *,
    detail: str | None = None,
    current_state: Mapping[str, Any] | None = None,
    command_id: str | None = None,
    command_type: str | None = None,
    run_id: str | None = None,
    recoverable: bool | None = None,
    source: str | None = None,
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    rejection_code_text = _coerce_text(rejection_code)
    if not rejection_code_text:
        raise ValueError("rejection_code is required")

    message_text = _coerce_text(message)
    if not message_text:
        raise ValueError("message is required")

    rejection_payload: dict[str, Any] = {
        "type": "runtime_rejected",
        "rejection_code": rejection_code_text,
        "message": message_text,
        "recoverable": bool(True if recoverable is None else recoverable),
    }
    if detail is not None:
        detail_text = _coerce_text(detail)
        if detail_text:
            rejection_payload["detail"] = detail_text
    current_state_data = _coerce_mapping(current_state)
    if current_state_data:
        rejection_payload["current_state"] = _json_safe_copy(current_state_data)
    if command_id:
        rejection_payload["command_id"] = _coerce_text(command_id)
    if command_type:
        rejection_payload["command_type"] = _coerce_text(command_type)
    if run_id:
        rejection_payload["run_id"] = _coerce_text(run_id)
    if source:
        rejection_payload["source"] = _coerce_text(source)

    return build_backend_event_envelope(
        "runtime_rejected",
        rejection_payload,
        schema_version=RUNTIME_REJECTION_SCHEMA_VERSION,
        run_id=run_id,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def _run_context_mismatch_reason(
    current_state: Mapping[str, Any] | None,
    command_context: Mapping[str, Any] | None,
    *,
    command_type: str,
) -> str | None:
    current_state_data = _coerce_mapping(current_state)
    command_context_data = _coerce_mapping(command_context)
    current_run_id = _coerce_text(current_state_data.get("run_id"))
    command_run_id = _coerce_text(command_context_data.get("run_id"))
    if not current_run_id or not command_run_id or current_run_id == command_run_id:
        return None
    return (
        f"{command_type} run_id mismatch: "
        f"received {command_run_id!r} while active run is {current_run_id!r}"
    )


def build_run_completed_payload(
    *,
    run_id: str,
    summary: str,
    recorded_count: int,
    skipped_count: int,
    failed_count: int = 0,
    code_status: str = "not_generated",
    phase: str = "completed",
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")

    summary_text = _coerce_text(summary)
    if not summary_text:
        raise ValueError("summary is required")

    recorded = int(recorded_count)
    skipped = int(skipped_count)
    failed = int(failed_count)
    if recorded < 0:
        raise ValueError("recorded_count must be non-negative")
    if skipped < 0:
        raise ValueError("skipped_count must be non-negative")
    if failed < 0:
        raise ValueError("failed_count must be non-negative")

    payload = {
        "run_id": run_id_text,
        "summary": summary_text,
        "recorded_count": recorded,
        "skipped_count": skipped,
        "failed_count": failed,
        "code_status": _coerce_text(code_status) or "not_generated",
        "phase": _coerce_text(phase) or "completed",
    }
    return build_backend_event_envelope(
        "run_completed",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_recovery_needed_payload(
    *,
    run_id: str,
    step_id: str,
    error_summary: str,
    current_url: str,
    tried: list[dict[str, Any]] | None = None,
    options: list[str] | None = None,
    operation_id: str | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")

    step_id_text = _coerce_text(step_id)
    if not step_id_text:
        raise ValueError("step_id is required")

    error_summary_text = _coerce_text(error_summary)
    if not error_summary_text:
        raise ValueError("error_summary is required")

    current_url_text = _coerce_text(current_url) or "unknown"
    tried_items = _json_safe_copy(tried or [])
    if not tried_items:
        tried_items = [
            {
                "step_id": step_id_text,
                "status": "failed",
                "error_summary": error_summary_text,
            }
        ]

    payload: dict[str, Any] = {
        "run_id": run_id_text,
        "step_id": step_id_text,
        "error_summary": error_summary_text,
        "current_url": current_url_text,
        "tried": tried_items,
        "options": list(options or ["retry", "skip", "stop"]),
    }
    if operation_id:
        payload["operation_id"] = _coerce_text(operation_id)

    return build_backend_event_envelope(
        "recovery_needed",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_session_state_event(
    payload: Mapping[str, Any] | None,
    *,
    source: str | None = "server",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    payload_data = _coerce_mapping(payload)
    run_id = _coerce_text(payload_data.get("run_id"))
    if not run_id:
        raise ValueError("run_id is required")

    phase = _coerce_text(payload_data.get("phase")) or "planning"

    session_state_payload: dict[str, Any] = {
        "run_id": run_id,
        "phase": phase,
        # pending steps (may be keyed as "steps" or "pending_steps")
        "steps": _json_safe_copy(payload_data.get("steps") or payload_data.get("pending_steps") or []),
        "recorded_steps": _json_safe_copy(payload_data.get("recorded_steps") or []),
    }

    # Sprint 7 Cluster 1 — S7-0110: full reconnect payload fields
    if "pending_steps" in payload_data:
        session_state_payload["pending_steps"] = _json_safe_copy(payload_data["pending_steps"] or [])

    plan_val = payload_data.get("plan")
    if plan_val is not None:
        session_state_payload["plan"] = _json_safe_copy(plan_val)

    code_preview = payload_data.get("code_preview")
    session_state_payload["code_preview"] = _coerce_text(code_preview) if code_preview is not None else None

    recovery_state = payload_data.get("recovery_state")
    if recovery_state is not None:
        session_state_payload["recovery_state"] = _json_safe_copy(recovery_state)
    else:
        session_state_payload["recovery_state"] = None

    replay_state = payload_data.get("replay_state")
    if replay_state is not None:
        session_state_payload["replay_state"] = _json_safe_copy(replay_state)
    else:
        session_state_payload["replay_state"] = None

    return build_backend_event_envelope(
        "session_state",
        session_state_payload,
        run_id=run_id,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


# ---------------------------------------------------------------------------
# Sprint 7 Cluster 1 — new event builders (S7-0101 through S7-0110)
# ---------------------------------------------------------------------------

def build_run_started_payload(
    run_id: str,
    steps: list[Any],
    phase: str = "planning",
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0101: Emit when a new run begins. PRD-04-BE-001."""
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")
    if steps is None:
        raise TypeError("steps must be a list, got None")

    payload = {
        "run_id": run_id_text,
        "steps": _json_safe_copy(list(steps)),
        "phase": _coerce_text(phase) or "planning",
    }
    return build_backend_event_envelope(
        "run_started",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_step_validating_payload(
    step_id: str,
    run_id: str,
    *,
    operation_id: str | None = None,
    locator: str | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0102: Emit before validation of a step/operation. PRD-04-BE-002."""
    step_id_text = _coerce_text(step_id)
    if not step_id_text:
        raise ValueError("step_id is required")
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")

    payload: dict[str, Any] = {
        "step_id": step_id_text,
        "run_id": run_id_text,
    }
    if operation_id:
        payload["operation_id"] = _coerce_text(operation_id)
    if locator:
        payload["locator"] = _coerce_text(locator)

    return build_backend_event_envelope(
        "step_validating",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_step_executing_payload(
    step_id: str,
    run_id: str,
    action: str,
    *,
    operation_id: str | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0102: Emit when a step action is about to execute. PRD-04-BE-003."""
    step_id_text = _coerce_text(step_id)
    if not step_id_text:
        raise ValueError("step_id is required")
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")
    action_text = _coerce_text(action)
    if not action_text:
        raise ValueError("action is required")

    payload: dict[str, Any] = {
        "step_id": step_id_text,
        "run_id": run_id_text,
        "action": action_text,
    }
    if operation_id:
        payload["operation_id"] = _coerce_text(operation_id)

    return build_backend_event_envelope(
        "step_executing",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_step_failed_payload(
    step_id: str,
    run_id: str,
    error: str,
    status: str,
    *,
    operation_id: str | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0103: Emit when a step execution fails. PRD-04-BE-004."""
    step_id_text = _coerce_text(step_id)
    if not step_id_text:
        raise ValueError("step_id is required")
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")
    error_text = _coerce_text(error)
    if not error_text:
        raise ValueError("error is required")

    payload: dict[str, Any] = {
        "step_id": step_id_text,
        "run_id": run_id_text,
        "error": error_text,
        "status": _coerce_text(status) or "failed",
    }
    if operation_id:
        payload["operation_id"] = _coerce_text(operation_id)

    return build_backend_event_envelope(
        "step_failed",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_step_skipped_payload(
    step_id: str,
    run_id: str,
    reason: str,
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0103: Emit when a step is deliberately skipped. PRD-04-BE-005."""
    step_id_text = _coerce_text(step_id)
    if not step_id_text:
        raise ValueError("step_id is required")
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")
    reason_text = _coerce_text(reason)
    if not reason_text:
        raise ValueError("reason is required")

    payload: dict[str, Any] = {
        "step_id": step_id_text,
        "run_id": run_id_text,
        "reason": reason_text,
    }
    return build_backend_event_envelope(
        "step_skipped",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_permission_required_payload(
    run_id: str,
    operation_id: str,
    action_type: str,
    risk_level: str,
    message: str,
    *,
    options: list[str] | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0104: Emit when policy requires a user decision before proceeding. PRD-04-BE-006."""
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")
    operation_id_text = _coerce_text(operation_id)
    if not operation_id_text:
        raise ValueError("operation_id is required")
    action_type_text = _coerce_text(action_type)
    if not action_type_text:
        raise ValueError("action_type is required")
    risk_level_text = _coerce_text(risk_level)
    if not risk_level_text:
        raise ValueError("risk_level is required")
    message_text = _coerce_text(message)
    if not message_text:
        raise ValueError("message is required")

    payload: dict[str, Any] = {
        "run_id": run_id_text,
        "operation_id": operation_id_text,
        "action_type": action_type_text,
        "risk_level": risk_level_text,
        "message": message_text,
    }
    if options is not None:
        payload["options"] = list(options)

    return build_backend_event_envelope(
        "permission_required",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_agent_settings_event(
    *,
    extra_agents: list[dict[str, Any]] | None = None,
    version: int | None = None,
    control_mode: str | None = None,
    source: str | None = "server",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """E1 (Backend Seam B1) — typed agent_settings event.

    Sprint 7 emits in read-only mode because runtime cannot yet truly
    enable/disable agents. The S9 denylist runs inside
    ``build_agent_settings_payload`` so no secret leaks even if a
    registry entry mistakenly adds one.
    """
    from runtime.agent_registry import build_agent_settings_payload

    kwargs: dict[str, Any] = {}
    if extra_agents is not None:
        kwargs["extra_agents"] = extra_agents
    if version is not None:
        kwargs["version"] = version
    if control_mode is not None:
        kwargs["control_mode"] = control_mode
    payload = build_agent_settings_payload(**kwargs)

    return build_backend_event_envelope(
        "agent_settings",
        payload,
        event_id=event_id or str(uuid4()),
        emitted_at=emitted_at,
        source=source,
    )


def build_typed_ready_envelope(
    session_id: str,
    workspace: str,
    mode: str,
    url: str,
    *,
    backend_ready: bool = True,
    browser_ready: bool = False,
    session_active: bool = False,
    source: str | None = "server",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0105: Typed ready envelope replacing plain status string. PRD-04-BE-007."""
    session_id_text = _coerce_text(session_id)
    if not session_id_text:
        raise ValueError("session_id is required")

    payload: dict[str, Any] = {
        "session_id": session_id_text,
        "workspace": _coerce_text(workspace),
        "mode": _coerce_text(mode),
        "url": _coerce_text(url),
        "backend_ready": bool(backend_ready),
        "browser_ready": bool(browser_ready),
        "session_active": bool(session_active),
    }
    return build_backend_event_envelope(
        "ready",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_browser_ready_event(
    *,
    browser_ready: bool = True,
    context: str | None = None,
    url: str | None = None,
    source: str | None = "server",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0105: Companion browser_ready event. PRD-04-BE-007."""
    payload: dict[str, Any] = {
        "browser_ready": bool(browser_ready),
    }
    if context:
        payload["context"] = _coerce_text(context)
    if url:
        payload["url"] = _coerce_text(url)

    return build_backend_event_envelope(
        "browser_ready",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_stop_run_result_event(
    run_id: str,
    status: str,
    *,
    reason: str | None = None,
    source: str | None = "server",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0107: Typed confirmation event after stop_run command is processed. PRD-04-CMD-001."""
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")
    status_text = _coerce_text(status)
    if not status_text:
        raise ValueError("status is required")

    payload: dict[str, Any] = {
        "run_id": run_id_text,
        "status": status_text,
    }
    if reason:
        payload["reason"] = _coerce_text(reason)

    return build_backend_event_envelope(
        "run_stopped",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_save_result_event(
    path: str,
    name: str,
    session_id: str,
    step_count: int,
    *,
    source: str | None = "server",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0109: Emitted after successful save_session. PRD-04-BE-save-load."""
    payload: dict[str, Any] = {
        "path": _coerce_text(path),
        "name": _coerce_text(name),
        "session_id": _coerce_text(session_id),
        "step_count": int(step_count),
    }
    return build_backend_event_envelope(
        "save_result",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_load_result_event(
    path: str,
    name: str,
    session_id: str,
    step_count: int,
    snapshot_valid: bool,
    *,
    source: str | None = "server",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """S7-0109: Emitted after successful load_session. PRD-04-BE-save-load."""
    payload: dict[str, Any] = {
        "path": _coerce_text(path),
        "name": _coerce_text(name),
        "session_id": _coerce_text(session_id),
        "step_count": int(step_count),
        "snapshot_valid": bool(snapshot_valid),
    }
    return build_backend_event_envelope(
        "load_result",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def _normalize_command_payload(
    message_data: Mapping[str, Any],
    *,
    current_state: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_message = _coerce_mapping(message_data)
    state_data = _coerce_mapping(current_state)

    payload = _coerce_mapping(raw_message.get("payload"))
    for key in ("run_id", "plan_id", "step_id", "step_number", "operation_id", "message", "answer", "value", "stop_on_error", "path", "name", "constraints"):
        if key in payload:
            continue
        value = raw_message.get(key)
        if value not in (None, "", [], {}):
            payload[key] = _json_safe_copy(value)

    normalized_context = {
        "run_id": _coerce_text(payload.get("run_id") or raw_message.get("run_id") or state_data.get("run_id")),
        "plan_id": _coerce_text(payload.get("plan_id") or raw_message.get("plan_id") or state_data.get("plan_id")),
        "step_id": _coerce_text(payload.get("step_id") or raw_message.get("step_id") or state_data.get("step_id")),
        "operation_id": _coerce_text(
            payload.get("operation_id") or raw_message.get("operation_id") or state_data.get("operation_id")
        ),
        "message": _coerce_text(payload.get("message") or raw_message.get("message")),
        "answer": _coerce_text(payload.get("answer") or raw_message.get("answer")),
        "value": _coerce_text(payload.get("value") or raw_message.get("value")),
        "stop_on_error": raw_message.get("stop_on_error") if "stop_on_error" in raw_message else payload.get("stop_on_error"),
        "path": _coerce_text(payload.get("path") or raw_message.get("path")),
        "name": _coerce_text(payload.get("name") or raw_message.get("name")),
        "constraints": _json_safe_copy(payload.get("constraints") or raw_message.get("constraints") or {}),
    }
    return payload, normalized_context


def normalize_frontend_command(
    message_data: Mapping[str, Any],
    *,
    current_state: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    raw_message = _coerce_mapping(message_data)
    state_data = _coerce_mapping(current_state)

    command_type = _coerce_text(raw_message.get("type"))
    if not command_type:
        return (
            None,
            build_runtime_rejection_payload(
                "MALFORMED_COMMAND",
                "Command type is required.",
                detail="missing type",
                current_state=state_data,
                command_id=_coerce_text(raw_message.get("command_id")) or None,
                run_id=_coerce_text(state_data.get("run_id")) or None,
                recoverable=False,
                source=_coerce_text(raw_message.get("source")) or None,
            ),
        )

    schema_version = _coerce_text(raw_message.get("schema_version"))
    command_id = _coerce_text(raw_message.get("command_id"))
    source = _coerce_text(raw_message.get("source"))

    if bool(schema_version) ^ bool(command_id):
        return (
            None,
            build_runtime_rejection_payload(
                "MALFORMED_COMMAND",
                "Canonical commands require both schema_version and command_id.",
                detail="command envelope is incomplete",
                current_state=state_data,
                command_id=command_id or None,
                run_id=_coerce_text(state_data.get("run_id")) or None,
                recoverable=False,
                source=source or None,
            ),
        )

    if schema_version and schema_version != FRONTEND_COMMAND_SCHEMA_VERSION:
        return (
            None,
            build_runtime_rejection_payload(
                "UNSUPPORTED_COMMAND_VERSION",
                f"Unsupported command schema_version: {schema_version}",
                detail="command envelope version mismatch",
                current_state=state_data,
                command_id=command_id or None,
                run_id=_coerce_text(state_data.get("run_id")) or None,
                recoverable=False,
                source=source or None,
            ),
        )

    payload, normalized_context = _normalize_command_payload(raw_message, current_state=state_data)
    is_canonical = bool(schema_version and command_id)
    is_legacy = not schema_version and not command_id

    if command_type not in SUPPORTED_FRONTEND_COMMAND_TYPES:
        return (
            None,
            build_runtime_rejection_payload(
                "COMMAND_NOT_SUPPORTED",
                f"Unsupported command: {command_type}",
                detail="command type is not handled by this backend slice",
                current_state=state_data,
                command_id=command_id or None,
                run_id=normalized_context["run_id"] or None,
                recoverable=False,
                source=source or None,
            ),
        )

    if command_type in {"confirmed", "correction"}:
        mismatch_reason = _run_context_mismatch_reason(
            state_data,
            normalized_context,
            command_type=command_type,
        )
        if mismatch_reason:
            return (
                None,
                build_runtime_rejection_payload(
                    "STALE_COMMAND",
                    f"{command_type} does not match the active run context.",
                    detail=mismatch_reason,
                    current_state=state_data,
                    command_id=command_id or None,
                    command_type=command_type,
                    run_id=normalized_context["run_id"] or None,
                    recoverable=False,
                    source=source or None,
                ),
            )

    if is_canonical:
        if command_type == "confirmed":
            run_id = normalized_context["run_id"]
            if not run_id:
                return (
                    None,
                    build_runtime_rejection_payload(
                        "MALFORMED_COMMAND",
                        "confirmed requires a run_id or active run context.",
                        detail="confirmed command missing run context",
                        current_state=state_data,
                        command_id=command_id,
                        run_id=_coerce_text(state_data.get("run_id")) or None,
                        recoverable=False,
                        source=source or "frontend",
                    ),
                )
        elif command_type == "correction":
            if not normalized_context["message"]:
                return (
                    None,
                    build_runtime_rejection_payload(
                        "MALFORMED_COMMAND",
                        "correction requires a message field.",
                        detail="correction command missing message",
                        current_state=state_data,
                        command_id=command_id,
                        run_id=normalized_context["run_id"] or None,
                        recoverable=False,
                        source=source or "frontend",
                    ),
                )
        elif command_type == "option_selected":
            if not normalized_context["value"] and not normalized_context["answer"]:
                return (
                    None,
                    build_runtime_rejection_payload(
                        "MALFORMED_COMMAND",
                        "option_selected requires a value field.",
                        detail="option_selected command missing value",
                        current_state=state_data,
                        command_id=command_id,
                        run_id=normalized_context["run_id"] or None,
                        recoverable=False,
                        source=source or "frontend",
                    ),
                )

        command_payload = dict(payload)
        command = build_frontend_command_envelope(
            command_type,
            command_payload,
            command_id=command_id,
            source=source or "frontend",
            run_id=normalized_context["run_id"] or None,
        )
        for key in ("message", "answer", "value", "run_id", "plan_id", "step_id", "operation_id", "stop_on_error", "path", "name", "constraints"):
            if key in normalized_context and normalized_context[key] not in (None, "", [], {}):
                command[key] = normalized_context[key]
        command["payload"] = _json_safe_copy(command_payload)
        return command, None

    if not is_legacy:
        return (
            None,
            build_runtime_rejection_payload(
                "MALFORMED_COMMAND",
                "Unsupported command envelope.",
                detail="command envelope is incomplete",
                current_state=state_data,
                command_id=command_id or None,
                run_id=normalized_context["run_id"] or None,
                recoverable=False,
                source=source or None,
            ),
        )

    command_payload = dict(payload)
    command = build_frontend_command_envelope(
        command_type,
        command_payload,
        command_id=f"cmd-{uuid4().hex}",
        source="legacy",
        run_id=normalized_context["run_id"] or None,
    )
    for key in ("message", "answer", "value", "run_id", "plan_id", "step_id", "operation_id", "stop_on_error", "path", "name", "constraints"):
        if key in normalized_context and normalized_context[key] not in (None, "", [], {}):
            command[key] = normalized_context[key]
    command["payload"] = _json_safe_copy(command_payload)
    return command, None


# ---------------------------------------------------------------------------
# Sprint 7 Cluster 2 — new event builders (S7-0201 through S7-0209)
# ---------------------------------------------------------------------------

def _redact_api_keys(text: str) -> str:
    return re.sub(r"sk-[^\s\"']+", "[REDACTED]", text)


def build_page_analysis_started_event(
    request_id: str,
    page_url: str,
    *,
    analysis_type: str = "fallback",
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    request_id_text = _coerce_text(request_id)
    if not request_id_text:
        raise ValueError("request_id is required")
    page_url_text = _coerce_text(page_url)
    if not page_url_text:
        raise ValueError("page_url is required")

    payload: dict[str, Any] = {
        "request_id": request_id_text,
        "page_url": page_url_text,
        "analysis_type": _coerce_text(analysis_type) or "fallback",
    }
    return build_backend_event_envelope(
        "page_analysis_started",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_page_summary_ready_event(
    request_id: str,
    page_summary: dict[str, Any],
    *,
    source: str | None = None,
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    request_id_text = _coerce_text(request_id)
    if not request_id_text:
        raise ValueError("request_id is required")
    if not isinstance(page_summary, Mapping):
        raise TypeError("page_summary must be a dict")

    safe_summary = {k: v for k, v in page_summary.items() if k != "raw_html"}

    payload: dict[str, Any] = {
        "request_id": request_id_text,
        "page_summary": _json_safe_copy(safe_summary),
    }
    return build_backend_event_envelope(
        "page_summary_ready",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_page_analysis_failed_event(
    request_id: str,
    page_url: str,
    reason: str,
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    request_id_text = _coerce_text(request_id)
    if not request_id_text:
        raise ValueError("request_id is required")
    reason_text = _coerce_text(reason)
    if not reason_text:
        raise ValueError("reason is required")

    payload: dict[str, Any] = {
        "request_id": request_id_text,
        "page_url": _coerce_text(page_url),
        "reason": reason_text,
    }
    return build_backend_event_envelope(
        "page_analysis_failed",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_recommendation_ready_event(
    request_id: str,
    recommendations: list[dict[str, Any]],
    *,
    min_confidence: float | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    request_id_text = _coerce_text(request_id)
    if not request_id_text:
        raise ValueError("request_id is required")
    if not isinstance(recommendations, list):
        raise TypeError("recommendations must be a list")

    copied = _json_safe_copy(list(recommendations))
    if min_confidence is not None:
        copied = [r for r in copied if r.get("confidence", 0) >= min_confidence]

    payload: dict[str, Any] = {
        "request_id": request_id_text,
        "recommendations": copied,
    }
    return build_backend_event_envelope(
        "recommendation_ready",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_capability_gap_event(
    action: str,
    reason: str,
    next_legal_action: str,
    *,
    severity: str = "error",
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    action_text = _coerce_text(action)
    if not action_text:
        raise ValueError("action is required")
    reason_text = _coerce_text(reason)
    if not reason_text:
        raise ValueError("reason is required")
    next_text = _coerce_text(next_legal_action)
    if not next_text:
        raise ValueError("next_legal_action is required")

    payload: dict[str, Any] = {
        "action": action_text,
        "reason": reason_text,
        "next_legal_action": next_text,
        "severity": _coerce_text(severity) or "error",
    }
    return build_backend_event_envelope(
        "capability_gap",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_schema_error_event(
    purpose: str,
    error_type: str,
    error_message: str,
    retry_count: int,
    max_retries: int,
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    purpose_text = _coerce_text(purpose)
    if not purpose_text:
        raise ValueError("purpose is required")
    error_type_text = _coerce_text(error_type)
    if not error_type_text:
        raise ValueError("error_type is required")
    if int(retry_count) < 0:
        raise ValueError("retry_count must be non-negative")

    safe_message = _redact_api_keys(_coerce_text(error_message))

    payload: dict[str, Any] = {
        "purpose": purpose_text,
        "error_type": error_type_text,
        "error_message": safe_message,
        "retry_count": int(retry_count),
        "max_retries": int(max_retries),
    }
    return build_backend_event_envelope(
        "schema_error",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_provider_error_event(
    purpose: str,
    error_type: str,
    error_message: str,
    retryable: bool,
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    purpose_text = _coerce_text(purpose)
    if not purpose_text:
        raise ValueError("purpose is required")
    error_type_text = _coerce_text(error_type)
    if not error_type_text:
        raise ValueError("error_type is required")

    safe_message = _redact_api_keys(_coerce_text(error_message))

    payload: dict[str, Any] = {
        "purpose": purpose_text,
        "error_type": error_type_text,
        "error_message": safe_message,
        "retryable": bool(retryable),
    }
    return build_backend_event_envelope(
        "provider_error",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_malformed_output_error_event(
    purpose: str,
    error_message: str,
    *,
    safe_output_sample: str | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    purpose_text = _coerce_text(purpose)
    if not purpose_text:
        raise ValueError("purpose is required")
    error_message_text = _coerce_text(error_message)
    if not error_message_text:
        raise ValueError("error_message is required")

    payload: dict[str, Any] = {
        "purpose": purpose_text,
        "error_message": error_message_text,
    }
    if safe_output_sample is not None:
        payload["safe_output_sample"] = _coerce_text(safe_output_sample)[:2000]

    return build_backend_event_envelope(
        "malformed_output_error",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_plan_diff_proposed_event(
    plan_id: str,
    old_version: int,
    new_version: int,
    operations: list[dict[str, Any]],
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    plan_id_text = _coerce_text(plan_id)
    if not plan_id_text:
        raise ValueError("plan_id is required")
    if not isinstance(operations, list):
        raise TypeError("operations must be a list")

    payload: dict[str, Any] = {
        "plan_id": plan_id_text,
        "old_version": int(old_version),
        "new_version": int(new_version),
        "operations": _json_safe_copy(operations),
    }
    return build_backend_event_envelope(
        "plan_diff_proposed",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_plan_diff_validated_event(
    plan_id: str,
    validation_status: str,
    issues: list[str],
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    plan_id_text = _coerce_text(plan_id)
    if not plan_id_text:
        raise ValueError("plan_id is required")
    status_text = _coerce_text(validation_status)
    if not status_text:
        raise ValueError("validation_status is required")

    payload: dict[str, Any] = {
        "plan_id": plan_id_text,
        "validation_status": status_text,
        "issues": list(issues),
    }
    return build_backend_event_envelope(
        "plan_diff_validated",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_plan_diff_applied_event(
    plan_id: str,
    result: str,
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    plan_id_text = _coerce_text(plan_id)
    if not plan_id_text:
        raise ValueError("plan_id is required")
    result_text = _coerce_text(result)
    if not result_text:
        raise ValueError("result is required")

    payload: dict[str, Any] = {
        "plan_id": plan_id_text,
        "result": result_text,
    }
    return build_backend_event_envelope(
        "plan_diff_applied",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_locator_candidates_ready_event(
    ambiguity_id: str,
    candidates: list[dict[str, Any]],
    *,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    ambiguity_id_text = _coerce_text(ambiguity_id)
    if not ambiguity_id_text:
        raise ValueError("ambiguity_id is required")
    if not isinstance(candidates, list):
        raise TypeError("candidates must be a list")

    safe_candidates = [
        {k: v for k, v in c.items() if k != "raw_dom"}
        for c in candidates
    ]

    payload: dict[str, Any] = {
        "ambiguity_id": ambiguity_id_text,
        "candidates": _json_safe_copy(safe_candidates),
    }
    return build_backend_event_envelope(
        "locator_candidates_ready",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_recovery_needed_structured_event(
    run_id: str,
    step_id: str,
    failure_reason: str,
    options: list[dict[str, Any]],
    *,
    expected: str | None = None,
    actual: str | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    run_id_text = _coerce_text(run_id)
    if not run_id_text:
        raise ValueError("run_id is required")
    step_id_text = _coerce_text(step_id)
    if not step_id_text:
        raise ValueError("step_id is required")
    failure_reason_text = _coerce_text(failure_reason)
    if not failure_reason_text:
        raise ValueError("failure_reason is required")
    if not isinstance(options, list):
        raise TypeError("options must be a list")
    if len(options) == 0:
        raise ValueError("options must not be empty")

    payload: dict[str, Any] = {
        "run_id": run_id_text,
        "step_id": step_id_text,
        "failure_reason": failure_reason_text,
        "options": _json_safe_copy(options),
    }
    if expected is not None:
        payload["expected"] = _coerce_text(expected)
    if actual is not None:
        payload["actual"] = _coerce_text(actual)

    return build_backend_event_envelope(
        "recovery_needed",
        payload,
        run_id=run_id_text,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )


def build_token_report_event(
    purpose: str,
    model_class: str,
    input_tokens: int,
    output_tokens: int,
    *,
    call_id: str | None = None,
    cached_tokens: int | None = None,
    latency_ms: int | None = None,
    estimated_cost: float | None = None,
    source: str | None = "agent",
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    purpose_text = _coerce_text(purpose)
    if not purpose_text:
        raise ValueError("purpose is required")
    model_class_text = _coerce_text(model_class)
    if not model_class_text:
        raise ValueError("model_class is required")
    if int(input_tokens) < 0:
        raise ValueError("input_tokens must be non-negative")
    if int(output_tokens) < 0:
        raise ValueError("output_tokens must be non-negative")

    payload: dict[str, Any] = {
        "purpose": purpose_text,
        "model_class": model_class_text,
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
    }
    if call_id is not None:
        payload["call_id"] = _coerce_text(call_id)
    if cached_tokens is not None:
        payload["cached_tokens"] = int(cached_tokens)
    if latency_ms is not None:
        payload["latency_ms"] = int(latency_ms)
    if estimated_cost is not None:
        payload["estimated_cost"] = float(estimated_cost)

    return build_backend_event_envelope(
        "token_report",
        payload,
        event_id=event_id,
        emitted_at=emitted_at,
        source=source,
    )
