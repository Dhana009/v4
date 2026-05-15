from __future__ import annotations

from collections.abc import Sequence

from runtime.tool_registry import PLANNING_SAFE_TOOL_NAMES

READ_ONLY_DOM_TOOL_NAMES: tuple[str, ...] = ("dom_extract",)
RECOVERY_ONLY_TOOL_NAMES: tuple[str, ...] = ("browser_get_state", "ask_user")
PLAN_REVIEW_ONLY_TOOL_NAMES: tuple[str, ...] = ("send_to_overlay", "ask_user")
EXECUTION_DRIVER_PLANNING_TOOL_NAMES: tuple[str, ...] = ("ask_user",)
STEP_PLAN_TOOL_NAMES: tuple[str, ...] = tuple(sorted(PLANNING_SAFE_TOOL_NAMES))


PURPOSE_PLANNING_TOOL_NAMES: dict[str, tuple[str, ...]] = {
    # --- classifiers (deterministic; LLM escalation must not invoke tools) ---
    "intent_classifier": (),
    "journey_classifier": (),
    "failure_classifier": (),
    "plan_edit_classifier": (),
    "locator_issue_classifier": (),
    "capability_classifier": (),
    # --- text-generation purposes (no browser interaction needed) ---
    "clarification_generator": PLAN_REVIEW_ONLY_TOOL_NAMES,
    "user_response_writer": ("ask_user",),
    "trace_summarizer": (),
    # --- read-only intelligence / analysis purposes ---
    "page_intelligence_summarizer": READ_ONLY_DOM_TOOL_NAMES,
    "page_validation_recommender": ("browser_get_state", "dom_extract", "ask_user"),
    # --- plan-construction purposes (read + overlay; no click/type/submit) ---
    # journey_planner retains full PLANNING_SAFE_TOOL_NAMES per contract test
    # (test_llm_planning_contracts §005). All tools are read-safe (no
    # action_click / action_fill / action_assert).
    "journey_planner": STEP_PLAN_TOOL_NAMES,
    "step_plan_normalizer": STEP_PLAN_TOOL_NAMES,
    "plan_diff_editor": (),
    # --- locator / assertion purposes (read-only DOM; no destructive actions) ---
    "locator_specialist": ("browser_get_state", "dom_extract", "locator_find", "locator_validate", "ask_user"),
    "custom_assertion_planner": ("browser_get_state", "dom_extract", "locator_find", "locator_validate", "ask_user"),
    # --- execution / recovery purposes ---
    "execution_driver": EXECUTION_DRIVER_PLANNING_TOOL_NAMES,
    "recovery_diagnoser": RECOVERY_ONLY_TOOL_NAMES,
    "replay_repair_specialist": RECOVERY_ONLY_TOOL_NAMES,
    # --- agent_fallback: read-safe planning surface (no destructive writes) ---
    # PLANNING_SAFE_TOOL_NAMES contains only: ask_user, browser_get_state,
    # dom_extract, locator_find, locator_validate, send_to_overlay — no
    # action_click / action_fill / action_assert. No downgrade required.
    "agent_fallback": STEP_PLAN_TOOL_NAMES,
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
