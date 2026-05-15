from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import re
from typing import Any


_TARGET_CHANGE_MARKERS = ("target", "locator", "selector", "element", "xpath", "css")


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


def _step_lines_from_plan(active_plan_state: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(active_plan_state, Mapping):
        return []

    lines: list[str] = []
    steps = active_plan_state.get("steps")
    if not isinstance(steps, list):
        return lines

    for step in steps:
        if not isinstance(step, Mapping):
            continue
        step_id = _normalize_text(step.get("step_id") or step.get("id"))
        intent = _normalize_text(step.get("intent") or step.get("title") or step.get("text") or step.get("label"))
        header_parts = [part for part in (step_id, intent) if part]
        if header_parts:
            lines.append(f"Parent step: {' | '.join(header_parts)}")
        expected_outcome = _normalize_text(step.get("expected_outcome") or step.get("expectedOutcome"))
        if expected_outcome:
            lines.append(f"  expected_outcome: {expected_outcome}")
        children = step.get("children")
        if not isinstance(children, list) or not children:
            lines.append("  child operations: none")
            continue
        for child in children:
            if not isinstance(child, Mapping):
                continue
            child_operation_id = _normalize_text(child.get("operation_id") or child.get("id"))
            child_type = _normalize_text(child.get("type") or child.get("action"))
            child_target = _normalize_text(child.get("target") or child.get("description"))
            child_locator = _normalize_text(child.get("locator"))
            child_parts = [part for part in (child_operation_id, child_type) if part]
            child_text = " ".join(child_parts) if child_parts else "child"
            if child_target:
                child_text += f' target="{child_target}"'
            if child_locator:
                child_text += f' locator="{child_locator}"'
            lines.append(f"  - {child_text}")
    return lines


def _locators_from_plan(active_plan_state: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(active_plan_state, Mapping):
        return []
    locators: list[str] = []
    steps = active_plan_state.get("steps")
    if not isinstance(steps, list):
        return locators
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        children = step.get("children")
        if not isinstance(children, list):
            continue
        for child in children:
            if not isinstance(child, Mapping):
                continue
            locator = _normalize_text(child.get("locator"))
            if locator and locator not in locators:
                locators.append(locator)
    return locators


def correction_needs_locator_context(
    correction_text: str | None,
    *,
    correction_state: Mapping[str, Any] | None = None,
) -> bool:
    text = _normalize_text(correction_text).lower()
    if any(marker in text for marker in _TARGET_CHANGE_MARKERS):
        return True
    if isinstance(correction_state, Mapping) and bool(correction_state.get("explicit_target_change")):
        return True
    return False


def build_plan_diff_editor_context_payload(
    *,
    active_plan_state: Mapping[str, Any] | None = None,
    correction_state: Mapping[str, Any] | None = None,
    correction_text: str | None = None,
    validated_locators: Sequence[str] | None = None,
    validation_feedback: str | None = None,
    allowed_edit_policy: str | None = None,
) -> dict[str, Any]:
    active_plan = dict(active_plan_state or {})
    correction = dict(correction_state or {})

    normalized_correction_text = _normalize_text(
        correction_text
        or correction.get("correction_text")
        or correction.get("correction")
        or correction.get("message")
    )
    plan_id = _normalize_text(correction.get("plan_id") or active_plan.get("plan_id"))
    target_step_id = _normalize_text(correction.get("target_step_id") or active_plan.get("target_step_id"))
    active_plan_summary = _normalize_text(
        active_plan.get("summary")
        or active_plan.get("original_user_intent")
        or active_plan.get("intent")
    )
    child_operations = _step_lines_from_plan(active_plan)
    locators = [
        locator
        for locator in (
            list(validated_locators or [])
            or _locators_from_plan(active_plan)
        )
        if _normalize_text(locator)
    ]
    normalized_locators = []
    for locator in locators:
        text = _normalize_text(locator)
        if text and text not in normalized_locators:
            normalized_locators.append(text)

    validation_feedback_text = _normalize_text(
        validation_feedback
        or correction.get("last_validation_feedback")
        or correction.get("last_validation_reason")
    )
    allowed_policy = _normalize_text(
        allowed_edit_policy
        or correction.get("allowed_edit_policy")
        or "preserve existing child operations; preserve order; no split or merge unless explicit; backend validates and applies the diff."
    )
    requires_locator_context = correction_needs_locator_context(
        normalized_correction_text,
        correction_state=correction,
    )

    return {
        "active_plan_id": plan_id,
        "target_step_id": target_step_id,
        "correction_text": normalized_correction_text,
        "active_plan_summary": active_plan_summary,
        "child_operations": "; ".join(child_operations),
        "validated_locators": _stringify_list(normalized_locators),
        "validation_feedback": validation_feedback_text,
        "allowed_edit_policy": allowed_policy,
        "locator_context_required": "yes" if requires_locator_context else "no",
    }


def render_plan_diff_editor_context(payload: Mapping[str, Any] | None = None) -> str:
    context = dict(payload or {})
    child_operations = _normalize_text(context.get("child_operations"))
    if not child_operations:
        child_operations = "none"
    lines = [
        "DYNAMIC_CORRECTION_CONTEXT:",
        "Structured correction diff context.",
        f"- Active plan id: {_normalize_text(context.get('active_plan_id'))}",
        f"- Target step id: {_normalize_text(context.get('target_step_id'))}",
        f"- User correction: {_normalize_text(context.get('correction_text'))}",
        f"- Active plan summary: {_normalize_text(context.get('active_plan_summary'))}",
        f"- Existing child operations: {child_operations}",
        f"- Validated locators available: {_normalize_text(context.get('validated_locators'))}",
        f"- Validation feedback: {_normalize_text(context.get('validation_feedback'))}",
        f"- Allowed edit policy: {_normalize_text(context.get('allowed_edit_policy'))}",
        f"- Locator context required: {_normalize_text(context.get('locator_context_required')) or 'no'}",
    ]
    return "\n".join(lines).strip()


def build_plan_diff_editor_schema_message(payload: Mapping[str, Any] | None = None) -> str:
    context = dict(payload or {})
    lines = [
        "STRUCTURED_CORRECTION_SCHEMA:",
        'schema_id: "plan_diff_editor.v1"',
        'purpose: "plan_diff_editor"',
        "Return one JSON object and nothing else.",
        "Include target_step_id and a mutations list.",
        "Use only the allowed mutation ops: keep, add, remove, reorder, change_expected_outcome.",
        "Do not emit plan_ready, llm_thinking, or browser actions.",
        "Backend validates and applies the diff.",
    ]
    target_plan_id = _normalize_text(context.get("active_plan_id"))
    if target_plan_id:
        lines.insert(3, f'target_plan_id: "{target_plan_id}"')
    target_step_id = _normalize_text(context.get("target_step_id"))
    if target_step_id:
        lines.insert(4, f'target_step_id: "{target_step_id}"')
    correction_text = _normalize_text(context.get("correction_text"))
    if correction_text:
        lines.append(f'correction_intent: "{correction_text}"')
    return "\n".join(lines).strip()


def extract_plan_diff_editor_context_from_messages(
    messages: Sequence[Mapping[str, Any]] | None,
    *,
    active_plan_state: Mapping[str, Any] | None = None,
    correction_state: Mapping[str, Any] | None = None,
    validation_feedback: str | None = None,
    allowed_edit_policy: str | None = None,
) -> dict[str, Any]:
    candidate_text = ""
    schema_text = ""
    for message in reversed(list(messages or [])):
        if not isinstance(message, Mapping):
            continue
        role = _normalize_text(message.get("role")).lower()
        if role not in {"system", "user", "assistant"}:
            continue
        content = _normalize_text(message.get("content"))
        if not content:
            continue
        if not candidate_text and (
            "DYNAMIC_CORRECTION_CONTEXT:" in content
            or "Structured correction diff context." in content
            or "Structured plan correction event." in content
        ):
            candidate_text = content
        if not schema_text and "STRUCTURED_CORRECTION_SCHEMA:" in content:
            schema_text = content
        if candidate_text and schema_text:
            break

    extracted_plan_id = ""
    extracted_target_step_id = ""
    extracted_correction_text = ""
    extracted_plan_summary = ""
    extracted_child_operations: list[str] = []
    extracted_locators: list[str] = []
    extracted_validation_feedback = ""
    extracted_allowed_policy = ""
    locator_context_required = ""

    if candidate_text:
        lines = candidate_text.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if line == "DYNAMIC_CORRECTION_CONTEXT:":
                continue
            if line.startswith("- Active plan id:"):
                extracted_plan_id = line.split(":", 1)[1].strip()
            elif line.startswith("- Target step id:"):
                extracted_target_step_id = line.split(":", 1)[1].strip()
            elif line.startswith("- User correction:"):
                extracted_correction_text = line.split(":", 1)[1].strip()
            elif line.startswith("- Active plan summary:"):
                extracted_plan_summary = line.split(":", 1)[1].strip()
            elif line.startswith("- Validated locators available:"):
                extracted_locators = [item.strip() for item in line.split(":", 1)[1].split(";") if item.strip()]
            elif line.startswith("- Validation feedback:"):
                extracted_validation_feedback = line.split(":", 1)[1].strip()
            elif line.startswith("- Allowed edit policy:"):
                extracted_allowed_policy = line.split(":", 1)[1].strip()
            elif line.startswith("- Locator context required:"):
                locator_context_required = line.split(":", 1)[1].strip()
            elif line.startswith("- Existing child operations:"):
                remainder = line.split(":", 1)[1].strip()
                if remainder and remainder.lower() != "none":
                    extracted_child_operations.extend(
                        [item.strip() for item in remainder.split(";") if item.strip()]
                    )
            elif line.startswith("active_plan_id:"):
                extracted_plan_id = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("target_step_id:"):
                extracted_target_step_id = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("Correction:"):
                extracted_correction_text = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("Previous plan summary:"):
                extracted_plan_summary = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("Validation feedback:"):
                extracted_validation_feedback = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("Allowed edit policy:"):
                extracted_allowed_policy = line.split(":", 1)[1].strip().strip('"')

    if not extracted_correction_text:
        for message in reversed(list(messages or [])):
            if not isinstance(message, Mapping):
                continue
            if _normalize_text(message.get("role")).lower() != "user":
                continue
            latest_user_text = _normalize_text(message.get("content"))
            if not latest_user_text:
                continue
            lower_text = latest_user_text.lower()
            if lower_text.startswith("correction:"):
                latest_user_text = latest_user_text.split(":", 1)[1].strip()
            elif lower_text.startswith("user correction:"):
                latest_user_text = latest_user_text.split(":", 1)[1].strip()
            extracted_correction_text = latest_user_text
            break

    payload = build_plan_diff_editor_context_payload(
        active_plan_state=active_plan_state,
        correction_state=correction_state,
        correction_text=extracted_correction_text or None,
        validated_locators=extracted_locators or None,
        validation_feedback=validation_feedback or extracted_validation_feedback or None,
        allowed_edit_policy=allowed_edit_policy or extracted_allowed_policy or None,
    )
    if extracted_plan_id and not payload.get("active_plan_id"):
        payload["active_plan_id"] = extracted_plan_id
    if extracted_target_step_id and not payload.get("target_step_id"):
        payload["target_step_id"] = extracted_target_step_id
    if extracted_plan_summary and not payload.get("active_plan_summary"):
        payload["active_plan_summary"] = extracted_plan_summary
    if extracted_child_operations:
        payload["child_operations"] = "\n".join(extracted_child_operations)
    if locator_context_required and not payload.get("locator_context_required"):
        payload["locator_context_required"] = locator_context_required
    return payload
