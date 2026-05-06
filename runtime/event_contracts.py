from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

BACKEND_EVENT_SCHEMA_VERSION = "autoworkbench.event.v1"
FRONTEND_COMMAND_SCHEMA_VERSION = "autoworkbench.command.v1"
RUNTIME_REJECTION_SCHEMA_VERSION = "autoworkbench.rejection.v1"

SUPPORTED_FRONTEND_COMMAND_TYPES = {"confirmed", "correction", "option_selected"}


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


def build_run_completed_payload(
    *,
    run_id: str,
    summary: str,
    recorded_count: int,
    skipped_count: int,
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

    payload = {
        "run_id": run_id_text,
        "summary": summary_text,
        "recorded_count": int(recorded_count),
        "skipped_count": int(skipped_count),
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
