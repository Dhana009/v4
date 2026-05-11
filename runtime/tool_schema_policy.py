from __future__ import annotations

from collections.abc import Sequence

from runtime.tool_registry import PLANNING_SAFE_TOOL_NAMES

READ_ONLY_DOM_TOOL_NAMES: tuple[str, ...] = ("dom_extract",)
RECOVERY_ONLY_TOOL_NAMES: tuple[str, ...] = ("browser_get_state", "ask_user")
PLAN_REVIEW_ONLY_TOOL_NAMES: tuple[str, ...] = ("send_to_overlay", "ask_user")
EXECUTION_DRIVER_PLANNING_TOOL_NAMES: tuple[str, ...] = ("ask_user",)
STEP_PLAN_TOOL_NAMES: tuple[str, ...] = tuple(sorted(PLANNING_SAFE_TOOL_NAMES))


PURPOSE_PLANNING_TOOL_NAMES: dict[str, tuple[str, ...]] = {
    "intent_classifier": (),
    "clarification_generator": PLAN_REVIEW_ONLY_TOOL_NAMES,
    "page_intelligence_summarizer": READ_ONLY_DOM_TOOL_NAMES,
    "page_validation_recommender": ("browser_get_state", "dom_extract", "ask_user"),
    "journey_planner": STEP_PLAN_TOOL_NAMES,
    "step_plan_normalizer": STEP_PLAN_TOOL_NAMES,
    "plan_diff_editor": (),
    "locator_specialist": ("browser_get_state", "dom_extract", "locator_find", "locator_validate", "ask_user"),
    "custom_assertion_planner": ("browser_get_state", "dom_extract", "locator_find", "locator_validate", "ask_user"),
    "execution_driver": EXECUTION_DRIVER_PLANNING_TOOL_NAMES,
    "recovery_diagnoser": RECOVERY_ONLY_TOOL_NAMES,
    "replay_repair_specialist": RECOVERY_ONLY_TOOL_NAMES,
    "user_response_writer": ("ask_user",),
    "trace_summarizer": (),
}


def planning_tools_for_purpose(purpose: str) -> tuple[str, ...]:
    normalized_purpose = str(purpose or "").strip()
    return PURPOSE_PLANNING_TOOL_NAMES.get(normalized_purpose, ())


def recovery_tools_for_purpose(purpose: str) -> tuple[str, ...]:
    normalized_purpose = str(purpose or "").strip()
    if normalized_purpose in {"recovery_diagnoser", "replay_repair_specialist"}:
        return RECOVERY_ONLY_TOOL_NAMES
    return ()


def normalize_tool_names(tool_names: Sequence[str] | None) -> list[str]:
    normalized: list[str] = []
    for name in tool_names or ():
        text = str(name or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized
