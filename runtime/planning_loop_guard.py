from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import json
from typing import Any

MAX_CONSECUTIVE_THINKING_ONLY_TURNS = 2
MAX_PLANNING_TURNS_WITHOUT_TERMINAL_OUTPUT = 3

THINKING_ONLY_MESSAGE_TYPE = "llm_thinking"
PLANNING_TERMINAL_MESSAGE_TYPES = {
    "plan_ready",
    "clarification_needed",
    "clarification",
    "step_recorded",
    "code_update",
    "llm_result",
    "runtime_rejected",
    "recovery_needed",
    "error",
    "plan_correction_diff",
}


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _message_value(message: Any, key: str) -> Any:
    if isinstance(message, Mapping):
        return message.get(key)
    return getattr(message, key, None)


def _tool_call_value(tool_call: Any, key: str) -> Any:
    if isinstance(tool_call, Mapping):
        return tool_call.get(key)
    return getattr(tool_call, key, None)


def _normalize_tool_calls(tool_calls: Any) -> list[Any]:
    if tool_calls is None:
        return []
    if isinstance(tool_calls, list):
        return list(tool_calls)
    if isinstance(tool_calls, tuple):
        return list(tool_calls)
    return [tool_calls]


def _tool_call_name(tool_call: Any) -> str:
    function = _tool_call_value(tool_call, "function")
    if isinstance(function, Mapping):
        name = function.get("name")
    else:
        name = getattr(function, "name", None)
    return _coerce_text(name).lower()


def _tool_call_arguments(tool_call: Any) -> dict[str, Any]:
    function = _tool_call_value(tool_call, "function")
    if isinstance(function, Mapping):
        arguments = function.get("arguments")
    else:
        arguments = getattr(function, "arguments", None)
    if isinstance(arguments, Mapping):
        return dict(arguments)
    if not isinstance(arguments, str):
        return {}
    try:
        parsed = json.loads(arguments)
    except Exception:  # noqa: BLE001
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


@dataclass(frozen=True, slots=True)
class PlanningLoopGuardState:
    consecutive_thinking_only_turns: int = 0
    planning_turns_without_terminal_output: int = 0


@dataclass(frozen=True, slots=True)
class PlanningLoopInspection:
    has_tool_calls: bool
    tool_names: tuple[str, ...]
    message_types: tuple[str, ...]
    content: str
    terminal_reason: str | None
    thinking_only: bool


@dataclass(frozen=True, slots=True)
class PlanningLoopGuardDecision:
    state: PlanningLoopGuardState
    inspection: PlanningLoopInspection
    should_stop: bool
    reason_code: str | None = None
    message: str | None = None
    detail: str | None = None


def inspect_planning_response(message: Any) -> PlanningLoopInspection:
    content = _coerce_text(_message_value(message, "content"))
    raw_tool_calls = _normalize_tool_calls(_message_value(message, "tool_calls"))

    tool_names: list[str] = []
    message_types: list[str] = []
    terminal_reason: str | None = None
    thinking_only = bool(raw_tool_calls)

    for tool_call in raw_tool_calls:
        tool_name = _tool_call_name(tool_call)
        if tool_name:
            tool_names.append(tool_name)

        if tool_name == "ask_user":
            message_types.append("ask_user")
            terminal_reason = terminal_reason or "ask_user"
            thinking_only = False
            continue

        if tool_name != "send_to_overlay":
            thinking_only = False
            continue

        payload = _tool_call_arguments(tool_call)
        message_type = _coerce_text(payload.get("message_type") or payload.get("type")).lower()
        if message_type:
            message_types.append(message_type)

        if message_type == THINKING_ONLY_MESSAGE_TYPE:
            continue

        thinking_only = False
        if message_type in PLANNING_TERMINAL_MESSAGE_TYPES:
            terminal_reason = terminal_reason or message_type

    if not raw_tool_calls and content:
        terminal_reason = "final_text"
    elif not raw_tool_calls and not content:
        thinking_only = False

    return PlanningLoopInspection(
        has_tool_calls=bool(raw_tool_calls),
        tool_names=tuple(tool_names),
        message_types=tuple(message_types),
        content=content,
        terminal_reason=terminal_reason,
        thinking_only=thinking_only,
    )


def advance_planning_loop_guard(
    state: PlanningLoopGuardState | None,
    message: Any,
    *,
    purpose: str | None = None,
    max_consecutive_thinking_only_turns: int = MAX_CONSECUTIVE_THINKING_ONLY_TURNS,
    max_planning_turns_without_terminal_output: int = MAX_PLANNING_TURNS_WITHOUT_TERMINAL_OUTPUT,
) -> PlanningLoopGuardDecision:
    current_state = state if isinstance(state, PlanningLoopGuardState) else PlanningLoopGuardState()
    inspection = inspect_planning_response(message)

    if inspection.terminal_reason is not None:
        return PlanningLoopGuardDecision(
            state=PlanningLoopGuardState(),
            inspection=inspection,
            should_stop=False,
        )

    next_planning_turns = current_state.planning_turns_without_terminal_output + 1
    next_thinking_turns = (
        current_state.consecutive_thinking_only_turns + 1
        if inspection.thinking_only
        else 0
    )
    next_state = replace(
        current_state,
        consecutive_thinking_only_turns=next_thinking_turns,
        planning_turns_without_terminal_output=next_planning_turns,
    )

    should_stop = (
        next_thinking_turns > max_consecutive_thinking_only_turns
        or next_planning_turns > max_planning_turns_without_terminal_output
    )
    if not should_stop:
        return PlanningLoopGuardDecision(
            state=next_state,
            inspection=inspection,
            should_stop=False,
        )

    purpose_text = _coerce_text(purpose) or "step_plan_normalizer"
    tool_names_text = ",".join(name for name in inspection.tool_names if name) or "none"
    message_types_text = ",".join(kind for kind in inspection.message_types if kind) or "none"
    detail = (
        f"purpose={purpose_text} "
        f"thinking_only_turns={next_thinking_turns} "
        f"max_consecutive_thinking_only_turns={max_consecutive_thinking_only_turns} "
        f"planning_turns_without_terminal_output={next_planning_turns} "
        f"max_planning_turns_without_terminal_output={max_planning_turns_without_terminal_output} "
        f"tool_names={tool_names_text} "
        f"message_types={message_types_text}"
    )
    return PlanningLoopGuardDecision(
        state=next_state,
        inspection=inspection,
        should_stop=True,
        reason_code="PLANNING_NO_PROGRESS",
        message="Planning did not produce plan_ready or clarification.",
        detail=detail,
    )
