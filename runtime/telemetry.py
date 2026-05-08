from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
import time
from typing import Any


def estimate_text_tokens(text: str) -> int:
    text = str(text or "")
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _message_payload_text(message: dict[str, Any]) -> str:
    parts: list[str] = []

    role = message.get("role")
    if role:
        parts.append(str(role))

    name = message.get("name")
    if name:
        parts.append(str(name))

    content = message.get("content")
    if isinstance(content, str):
        parts.append(content)
    elif content is not None:
        try:
            parts.append(json.dumps(content, ensure_ascii=True, separators=(",", ":")))
        except Exception:  # noqa: BLE001
            parts.append(str(content))

    tool_call_id = message.get("tool_call_id")
    if tool_call_id:
        parts.append(str(tool_call_id))

    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                parts.append(str(tool_call))
                continue
            function = tool_call.get("function")
            if isinstance(function, dict):
                function_name = function.get("name")
                function_arguments = function.get("arguments")
                if function_name:
                    parts.append(str(function_name))
                if function_arguments is not None:
                    parts.append(str(function_arguments))
            else:
                parts.append(str(tool_call))

    return " ".join(part for part in parts if part).strip()


def estimate_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for message in messages or []:
        if isinstance(message, dict):
            total += estimate_text_tokens(_message_payload_text(message)) + 4
        else:
            total += estimate_text_tokens(str(message)) + 4
    return total


def estimate_tools_tokens(tools: list[dict] | None) -> int:
    if not tools:
        return 0

    total = 0
    for tool in tools:
        try:
            serialized = json.dumps(tool, ensure_ascii=True, separators=(",", ":"))
        except Exception:  # noqa: BLE001
            serialized = str(tool)
        total += estimate_text_tokens(serialized) + 8
    return total


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sanitize_error_message(value: Any, limit: int = 180) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip()
    return text


def _usage_value(usage: Any, *names: str) -> int | None:
    if usage is None:
        return None

    if isinstance(usage, dict):
        for name in names:
            value = usage.get(name)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None

    for name in names:
        value = getattr(usage, name, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


@dataclass(slots=True)
class ModelCallTelemetry:
    timestamp: str
    call_id: str
    purpose: str
    model: str
    message_count: int
    estimated_message_tokens: int
    estimated_tools_tokens: int
    estimated_total_input_tokens: int
    skill_count: int
    tool_count: int
    started_at_monotonic: float = field(repr=False)
    success: bool | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    # Token category breakdown (INT-OBS-001)
    system_prompt_tokens: int | None = None
    skill_tokens: int | None = None
    tool_schema_tokens: int | None = None
    message_history_tokens: int | None = None
    dom_or_tool_result_tokens: int | None = None


def _count_dom_tool_result_tokens(messages: list[dict]) -> int:
    total = 0
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "") != "tool":
            continue
        content = message.get("content")
        if content is None:
            continue
        text = content if isinstance(content, str) else json.dumps(content, separators=(",", ":"))
        total += estimate_text_tokens(text)
    return total


def _count_system_tokens(messages: list[dict]) -> int:
    total = 0
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "") != "system":
            continue
        content = message.get("content") or ""
        total += estimate_text_tokens(content if isinstance(content, str) else json.dumps(content))
    return total


def _count_history_tokens(messages: list[dict]) -> int:
    total = 0
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "")
        if role in ("user", "assistant"):
            total += estimate_text_tokens(_message_payload_text(message)) + 4
    return total


def record_model_call_start(
    *,
    call_id: str,
    purpose: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None,
    skill_count: int = 0,
    skill_tokens: int | None = None,
) -> ModelCallTelemetry:
    message_count = len(messages or [])
    tool_count = len(tools or [])
    estimated_message_tokens = estimate_messages_tokens(messages)
    estimated_tools_tokens = estimate_tools_tokens(tools)
    system_prompt_tokens = _count_system_tokens(messages)
    message_history_tokens = _count_history_tokens(messages)
    dom_or_tool_result_tokens = _count_dom_tool_result_tokens(messages)
    tool_schema_tokens = estimated_tools_tokens
    return ModelCallTelemetry(
        timestamp=_utc_timestamp(),
        call_id=str(call_id or "").strip() or "llm_unknown",
        purpose=str(purpose or "").strip() or "unknown",
        model=str(model or "").strip() or "unknown",
        message_count=message_count,
        estimated_message_tokens=estimated_message_tokens,
        estimated_tools_tokens=estimated_tools_tokens,
        estimated_total_input_tokens=estimated_message_tokens + estimated_tools_tokens,
        skill_count=max(0, int(skill_count or 0)),
        tool_count=tool_count,
        started_at_monotonic=time.perf_counter(),
        system_prompt_tokens=system_prompt_tokens,
        skill_tokens=skill_tokens,
        tool_schema_tokens=tool_schema_tokens,
        message_history_tokens=message_history_tokens,
        dom_or_tool_result_tokens=dom_or_tool_result_tokens,
    )


def _format_telemetry_line(record: ModelCallTelemetry) -> str:
    parts = [
        "[LLM_TELEMETRY]",
        f"timestamp={record.timestamp}",
        f"call_id={record.call_id}",
        f"purpose={record.purpose}",
        f"model={record.model}",
        f"message_count={record.message_count}",
        f"estimated_message_tokens={record.estimated_message_tokens}",
        f"estimated_tools_tokens={record.estimated_tools_tokens}",
        f"estimated_total_input_tokens={record.estimated_total_input_tokens}",
        f"skill_count={record.skill_count}",
        f"tool_count={record.tool_count}",
        f"success={'true' if record.success else 'false'}",
    ]

    if record.system_prompt_tokens is not None:
        parts.append(f"system_prompt_tokens={record.system_prompt_tokens}")
    if record.skill_tokens is not None:
        parts.append(f"skill_tokens={record.skill_tokens}")
    if record.tool_schema_tokens is not None:
        parts.append(f"tool_schema_tokens={record.tool_schema_tokens}")
    if record.message_history_tokens is not None:
        parts.append(f"message_history_tokens={record.message_history_tokens}")
    if record.dom_or_tool_result_tokens is not None:
        parts.append(f"dom_or_tool_result_tokens={record.dom_or_tool_result_tokens}")
    if record.output_tokens is not None:
        parts.append(f"output_tokens={record.output_tokens}")
    if record.total_tokens is not None:
        parts.append(f"total_tokens={record.total_tokens}")
    if record.latency_ms is not None:
        parts.append(f"latency_ms={record.latency_ms}")
    if not record.success:
        if record.error_type:
            parts.append(f"error_type={record.error_type}")
        if record.error_message:
            parts.append(f"error_message={json.dumps(record.error_message, ensure_ascii=True)}")

    return " ".join(parts)


def record_model_call_end(
    record: ModelCallTelemetry,
    *,
    success: bool,
    response_usage: Any = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> ModelCallTelemetry:
    try:
        record.success = success
        record.latency_ms = max(0, int((time.perf_counter() - record.started_at_monotonic) * 1000))
        record.output_tokens = _usage_value(response_usage, "completion_tokens", "output_tokens")
        record.total_tokens = _usage_value(response_usage, "total_tokens")
        record.error_type = error_type if not success else None
        record.error_message = _sanitize_error_message(error_message) if (not success and error_message) else None
        print(_format_telemetry_line(record))
    except Exception:  # noqa: BLE001
        pass
    return record
