from __future__ import annotations

from runtime.llm_runtime_controller import PURPOSE_REGISTRY
from runtime.tool_schema_policy import planning_tools_for_purpose


def test_tool_policy_contract_matches_registry_for_key_purposes() -> None:
    expected = {
        "plan_diff_editor": set(),
        "recovery_diagnoser": {"browser_get_state", "ask_user"},
        "page_intelligence_summarizer": {"dom_extract"},
        "step_plan_normalizer": {
            "send_to_overlay",
            "browser_get_state",
            "dom_extract",
            "locator_find",
            "locator_validate",
            "ask_user",
        },
    }

    for purpose, expected_tools in expected.items():
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        assert set(planning_tools_for_purpose(purpose)) == expected_tools
        assert set(policy["tool_policy"]["allowed_tools_by_phase"]["planning"]) == expected_tools


def test_unknown_purpose_fails_safe_to_minimal_tool_set() -> None:
    assert planning_tools_for_purpose("unknown_future_purpose") == ()
