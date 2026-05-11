from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


_RECOVERY_FAILURE_MARKERS = ("failed", "failure", "error", "timeout", "retry", "blocked")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _stringify_list(values: Sequence[Any] | None) -> str:
    if isinstance(values, str):
        values = [values]
    parts: list[str] = []
    for value in values or ():
        text = _normalize_text(value)
        if text:
            parts.append(text)
    return "; ".join(parts)


def _step_summary_from_failed_step(failed_step: Mapping[str, Any] | None) -> str:
    if not isinstance(failed_step, Mapping):
        return ""

    parts: list[str] = []
    for key, label in (
        ("step_id", "step_id"),
        ("id", "step_id"),
        ("step_number", "step_number"),
        ("intent", "intent"),
        ("title", "title"),
        ("text", "text"),
        ("locator", "locator"),
        ("last_error", "last_error"),
        ("expected_outcome", "expected_outcome"),
    ):
        if key not in failed_step:
            continue
        value = _normalize_text(failed_step.get(key))
        if value:
            parts.append(f"{label}={value}")
    return " | ".join(parts)


def _latest_relevant_messages(messages: Sequence[Mapping[str, Any]] | None) -> tuple[str, list[str], list[str]]:
    failure_text = ""
    tried_fixes: list[str] = []
    evidence: list[str] = []
    for message in reversed(list(messages or [])):
        if not isinstance(message, Mapping):
            continue
        role = _normalize_text(message.get("role")).lower()
        content = _normalize_text(message.get("content"))
        if not content:
            continue
        lower_content = content.lower()
        if not failure_text and any(marker in lower_content for marker in _RECOVERY_FAILURE_MARKERS):
            failure_text = content
        if role == "assistant" and lower_content.startswith("recovery:"):
            tried_fixes.insert(0, content.split(":", 1)[1].strip())
        elif role == "assistant" and any(marker in lower_content for marker in ("retry", "repair", "re-evaluate", "recheck")):
            tried_fixes.insert(0, content)
        if role in {"assistant", "tool"} and any(marker in lower_content for marker in ("error", "timeout", "failed", "failure")):
            evidence.insert(0, content)
        if role == "user" and not evidence:
            evidence.insert(0, content)
    return failure_text, tried_fixes, evidence


def collect_retry_attempts_for_failed_step(
    retry_attempts: Sequence[Mapping[str, Any]] | None,
    failed_step_id: str | None,
) -> list[str]:
    normalized_step_id = _normalize_text(failed_step_id)
    if not normalized_step_id:
        return []

    collected: list[str] = []
    for attempt in retry_attempts or []:
        if not isinstance(attempt, Mapping):
            continue
        attempt_step_id = _normalize_text(
            attempt.get("failed_step_id")
            or attempt.get("step_id")
            or attempt.get("target_step_id")
        )
        if attempt_step_id != normalized_step_id:
            continue
        attempt_summary = _normalize_text(
            attempt.get("summary")
            or attempt.get("message")
            or attempt.get("reason")
            or attempt.get("error_summary")
            or attempt.get("error")
        )
        status = _normalize_text(attempt.get("status") or attempt.get("result"))
        parts = [f"step_id={attempt_step_id}"]
        if status:
            parts.append(f"status={status}")
        if attempt_summary:
            parts.append(attempt_summary)
        collected.append(" | ".join(parts))
    return collected


def build_recovery_diagnoser_context_payload(
    *,
    run_id: str | None = None,
    failed_step_state: Mapping[str, Any] | None = None,
    failed_step_id: str | None = None,
    failed_operation_id: str | None = None,
    error_summary: str | None = None,
    current_page: str | None = None,
    tried_fixes: Sequence[Any] | None = None,
    failure_evidence: Sequence[Any] | None = None,
    user_recovery_instruction: str | None = None,
    retry_attempts: Sequence[Any] | str | None = None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    failed_step = dict(failed_step_state or {})
    metadata_map = dict(metadata or {})
    message_failure_text, message_tried_fixes, message_evidence = _latest_relevant_messages(messages)

    def _coerce_items(values: Sequence[Any] | str | None, fallback: Sequence[Any] | None = None) -> list[str]:
        source: Sequence[Any] | None
        if values is None:
            source = fallback
        elif isinstance(values, str):
            source = [values]
        else:
            source = values
        items: list[str] = []
        for item in source or ():
            text = _normalize_text(item)
            if text:
                items.append(text)
        return items

    normalized_step_id = _normalize_text(
        failed_step_id
        or failed_step.get("step_id")
        or failed_step.get("id")
        or metadata_map.get("failed_step_id")
        or metadata_map.get("step_id")
    )
    normalized_operation_id = _normalize_text(
        failed_operation_id
        or failed_step.get("operation_id")
        or failed_step.get("failed_operation_id")
        or metadata_map.get("failed_operation_id")
    )
    normalized_run_id = _normalize_text(run_id or metadata_map.get("run_id"))
    normalized_error_summary = _normalize_text(
        error_summary
        or failed_step.get("last_error")
        or failed_step.get("error_summary")
        or failed_step.get("error")
        or message_failure_text
        or metadata_map.get("error_summary")
    )
    normalized_current_page = _normalize_text(
        current_page
        or metadata_map.get("current_page")
        or metadata_map.get("current_url")
        or metadata_map.get("page_title")
        or metadata_map.get("current_title")
    )
    normalized_tried_fixes = _coerce_items(tried_fixes, message_tried_fixes)
    normalized_failure_evidence = _coerce_items(failure_evidence, message_evidence)
    normalized_user_instruction = _normalize_text(
        user_recovery_instruction
        or metadata_map.get("user_recovery_instruction")
        or next(
            (
                _normalize_text(message.get("content"))
                for message in reversed(list(messages or []))
                if isinstance(message, Mapping) and _normalize_text(message.get("role")).lower() == "user"
            ),
            "",
        )
    )
    normalized_retry_attempts: list[str] = []
    if retry_attempts is not None:
        if isinstance(retry_attempts, str):
            retry_source: Sequence[Any] = [retry_attempts]
        else:
            retry_source = retry_attempts
        for attempt in retry_source:
            if isinstance(attempt, Mapping):
                attempt_step_id = _normalize_text(
                    attempt.get("failed_step_id")
                    or attempt.get("step_id")
                    or attempt.get("target_step_id")
                )
                if normalized_step_id and attempt_step_id != normalized_step_id:
                    continue
                attempt_summary = _normalize_text(
                    attempt.get("summary")
                    or attempt.get("message")
                    or attempt.get("reason")
                    or attempt.get("error_summary")
                    or attempt.get("error")
                )
                status = _normalize_text(attempt.get("status") or attempt.get("result"))
                parts = []
                if attempt_step_id:
                    parts.append(f"step_id={attempt_step_id}")
                if status:
                    parts.append(f"status={status}")
                if attempt_summary:
                    parts.append(attempt_summary)
                text = " | ".join(parts)
                if text:
                    normalized_retry_attempts.append(text)
            else:
                text = _normalize_text(attempt)
                if text:
                    normalized_retry_attempts.append(text)
    if not normalized_retry_attempts and normalized_step_id:
        normalized_retry_attempts = collect_retry_attempts_for_failed_step(retry_attempts if isinstance(retry_attempts, Sequence) else None, normalized_step_id)
    if not normalized_retry_attempts and normalized_step_id:
        for message in reversed(list(messages or [])):
            if not isinstance(message, Mapping):
                continue
            message_text = _normalize_text(message.get("content"))
            if not message_text:
                continue
            if normalized_step_id not in message_text:
                continue
            if any(marker in message_text.lower() for marker in ("retry", "attempt", "again")):
                normalized_retry_attempts.append(message_text)

    failed_step_summary = _step_summary_from_failed_step(failed_step)
    if not failed_step_summary and normalized_step_id:
        failed_step_summary = f"step_id={normalized_step_id}"

    return {
        "run_id": normalized_run_id,
        "failed_step_id": normalized_step_id,
        "failed_operation_id": normalized_operation_id,
        "failed_step_summary": failed_step_summary,
        "error_summary": normalized_error_summary,
        "current_page": normalized_current_page,
        "tried_fixes": _stringify_list(normalized_tried_fixes),
        "failure_evidence": _stringify_list(normalized_failure_evidence),
        "user_recovery_instruction": normalized_user_instruction,
        "retry_attempts": _stringify_list(normalized_retry_attempts),
    }


def render_recovery_diagnoser_context(payload: Mapping[str, Any] | None = None) -> str:
    context = dict(payload or {})
    lines = [
        "DYNAMIC_RECOVERY_CONTEXT:",
        "Recovery required for the failed original step.",
        f"- Run id: {_normalize_text(context.get('run_id'))}",
        f"- Failed step id: {_normalize_text(context.get('failed_step_id'))}",
        f"- Failed operation id: {_normalize_text(context.get('failed_operation_id'))}",
        f"- Failed step summary: {_normalize_text(context.get('failed_step_summary'))}",
        f"- Error summary: {_normalize_text(context.get('error_summary'))}",
        f"- Current URL/title: {_normalize_text(context.get('current_page'))}",
        f"- Tried fixes for this failed step: {_normalize_text(context.get('tried_fixes')) or 'none'}",
        f"- Relevant locator/action evidence: {_normalize_text(context.get('failure_evidence')) or 'none'}",
        f"- User recovery instruction: {_normalize_text(context.get('user_recovery_instruction')) or 'none'}",
        f"- Retry attempts for this failed step: {_normalize_text(context.get('retry_attempts')) or 'none'}",
    ]
    return "\n".join(lines).strip()


def extract_recovery_diagnoser_context_from_messages(
    messages: Sequence[Mapping[str, Any]] | None,
    *,
    metadata: Mapping[str, Any] | None = None,
    failed_step_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_text = ""
    for message in reversed(list(messages or [])):
        if not isinstance(message, Mapping):
            continue
        role = _normalize_text(message.get("role")).lower()
        if role not in {"system", "user", "assistant", "tool"}:
            continue
        content = _normalize_text(message.get("content"))
        if not content:
            continue
        if (
            "DYNAMIC_RECOVERY_CONTEXT:" in content
            or "Recovery required for the failed original step." in content
            or "failed step" in content.lower()
            or "recovery" in content.lower()
        ):
            candidate_text = content
            break

    parsed_metadata = dict(metadata or {})
    failed_step = dict(failed_step_state or {})
    failed_step_id = _normalize_text(
        failed_step.get("step_id")
        or failed_step.get("id")
        or parsed_metadata.get("failed_step_id")
        or parsed_metadata.get("step_id")
    )
    failed_operation_id = _normalize_text(
        failed_step.get("operation_id")
        or failed_step.get("failed_operation_id")
        or parsed_metadata.get("failed_operation_id")
    )
    error_summary = _normalize_text(
        failed_step.get("last_error")
        or failed_step.get("error_summary")
        or parsed_metadata.get("error_summary")
    )
    current_page = _normalize_text(
        parsed_metadata.get("current_page")
        or parsed_metadata.get("current_url")
        or parsed_metadata.get("page_title")
        or parsed_metadata.get("current_title")
    )
    user_instruction = _normalize_text(parsed_metadata.get("user_recovery_instruction"))
    retry_attempts = parsed_metadata.get("retry_attempts")

    if candidate_text:
        for raw_line in candidate_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("- Run id:") and not parsed_metadata.get("run_id"):
                parsed_metadata["run_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Failed step id:") and not failed_step_id:
                failed_step_id = line.split(":", 1)[1].strip()
            elif line.startswith("- Failed operation id:") and not failed_operation_id:
                failed_operation_id = line.split(":", 1)[1].strip()
            elif line.startswith("- Failed step summary:") and not failed_step:
                failed_step["summary"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Error summary:") and not error_summary:
                error_summary = line.split(":", 1)[1].strip()
            elif line.startswith("- Current URL/title:") and not current_page:
                current_page = line.split(":", 1)[1].strip()
            elif line.startswith("- Tried fixes for this failed step:") and "tried_fixes" not in parsed_metadata:
                parsed_metadata["tried_fixes"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Relevant locator/action evidence:") and "failure_evidence" not in parsed_metadata:
                parsed_metadata["failure_evidence"] = line.split(":", 1)[1].strip()
            elif line.startswith("- User recovery instruction:") and not user_instruction:
                user_instruction = line.split(":", 1)[1].strip()
            elif line.startswith("- Retry attempts for this failed step:") and retry_attempts is None:
                retry_attempts = line.split(":", 1)[1].strip()

    return build_recovery_diagnoser_context_payload(
        run_id=parsed_metadata.get("run_id"),
        failed_step_state=failed_step or None,
        failed_step_id=failed_step_id or None,
        failed_operation_id=failed_operation_id or None,
        error_summary=error_summary or None,
        current_page=current_page or None,
        tried_fixes=_normalize_text(parsed_metadata.get("tried_fixes")) or None,
        failure_evidence=_normalize_text(parsed_metadata.get("failure_evidence")) or None,
        user_recovery_instruction=user_instruction or None,
        retry_attempts=retry_attempts if retry_attempts is not None else None,
        messages=messages,
        metadata=metadata,
    )
