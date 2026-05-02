from __future__ import annotations

import json
from typing import Any


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _json_safe_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=True, sort_keys=True))


def _code_lines_from_code_updates(code_update_payloads: list[dict[str, Any]] | None) -> list[str]:
    if not isinstance(code_update_payloads, list) or not code_update_payloads:
        return []

    latest_payload = code_update_payloads[-1]
    if not isinstance(latest_payload, dict):
        return []

    lines = latest_payload.get("lines")
    if not isinstance(lines, list):
        return []

    code_lines: list[str] = []
    for line in lines:
        line_text = _coerce_text(line)
        if line_text:
            code_lines.append(line_text)
    return code_lines


def _code_lines_from_recorded_steps(recorded_steps: list[dict[str, Any]] | None) -> list[str]:
    if not isinstance(recorded_steps, list) or not recorded_steps:
        return []

    code_lines: list[str] = []
    for recorded_step in recorded_steps:
        if not isinstance(recorded_step, dict):
            continue

        step_lines: list[str] = []
        children = recorded_step.get("children")
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, dict):
                    continue
                child_code_lines = child.get("code_lines")
                if not isinstance(child_code_lines, list):
                    continue
                for code_line in child_code_lines:
                    code_line_text = _coerce_text(code_line)
                    if code_line_text:
                        step_lines.append(code_line_text)

        if step_lines:
            code_lines.extend(step_lines)
            continue

        generated_line = _coerce_text(recorded_step.get("generated_line"))
        if generated_line:
            code_lines.append(generated_line)

    return code_lines


def build_spec_snapshot(
    *,
    schema_version: str,
    session_id: str,
    created_at: str,
    original_user_intent: str | None,
    plan_ready: dict[str, Any] | None,
    recorded_steps: list[dict[str, Any]] | None,
    code_update_payloads: list[dict[str, Any]] | None,
    capability_gaps: list[dict[str, Any]] | None,
    phase: str,
    completed_step_count: int,
    recorded_step_count: int,
) -> dict[str, Any]:
    plan_ready_payload = plan_ready if isinstance(plan_ready, dict) else {}
    plan_ready_steps = plan_ready_payload.get("steps")
    if not isinstance(plan_ready_steps, list):
        plan_ready_steps = []

    plan_ready_snapshot = {
        "summary": _coerce_text(plan_ready_payload.get("summary")) or None,
        "steps": _json_safe_copy(plan_ready_steps),
    }

    recorded_steps_snapshot = _json_safe_copy(recorded_steps or [])
    capability_gaps_snapshot = _json_safe_copy(capability_gaps or [])

    has_code_update_payloads = isinstance(code_update_payloads, list) and bool(code_update_payloads)
    code_lines = _code_lines_from_code_updates(code_update_payloads)
    if not has_code_update_payloads:
        code_lines = _code_lines_from_recorded_steps(recorded_steps_snapshot)

    snapshot = {
        "schema_version": schema_version,
        "session_id": _coerce_text(session_id),
        "created_at": _coerce_text(created_at),
        "original_user_intent": _coerce_text(original_user_intent) or None,
        "plan_ready": plan_ready_snapshot,
        "recorded_steps": recorded_steps_snapshot,
        "code": {
            "lines": code_lines,
            "full_spec_preview": "\n".join(code_lines),
        },
        "capability_gaps": capability_gaps_snapshot,
        "metadata": {
            "phase": _coerce_text(phase) or "planning",
            "completed_step_count": int(completed_step_count),
            "recorded_step_count": int(recorded_step_count),
        },
    }
    return _json_safe_copy(snapshot)
