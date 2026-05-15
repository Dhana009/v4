"""
S6-0105: Plan edit and custom assertion purpose policies — unit and contract tests.

Purposes: plan_diff_editor, custom_assertion_planner.
Tests-first policy: all tests written before implementation.
Source rule: Runtime Policy Spec — editing/assertion purposes have specific tool constraints.

Key invariants tested:
- plan_diff_editor exposes no browser tools
- plan_diff_editor receives active plan context only (via context_policy)
- plan_diff_editor cannot silently drop child operations (policy declares validator)
- plan_diff_editor cannot silently reorder without explicit instruction (validator required)
- custom_assertion_planner uses inspection/context tools only
- custom_assertion_planner asks user when expected value is missing (via ask_user tool)
- unsupported assertion maps to capability_gap/fail-safe policy (fallback_policy)
- invalid schema retry/fail-closed behavior exists
"""
from __future__ import annotations

import pytest

from runtime.llm_policy_registry import build_default_registry, POLICY_REGISTRY

EDIT_ASSERT_PURPOSES = {
    "plan_diff_editor",
    "custom_assertion_planner",
}

BROWSER_TOOLS = frozenset({
    "action_click",
    "action_fill",
    "action_assert",
    "browser_navigate",
    "browser_back",
    "browser_forward",
    "dom_mutate",
    "record_step",
    "emit_recorded",
    "emit_completed",
})

RUNTIME_MUTATION_TOOLS = frozenset({
    "action_click",
    "action_fill",
    "action_assert",
    "record_step",
    "emit_recorded",
    "emit_completed",
    "mark_running",
    "mark_done",
})


@pytest.fixture()
def registry():
    return build_default_registry()


# ---------------------------------------------------------------------------
# plan_diff_editor — no browser tools
# ---------------------------------------------------------------------------

def test_plan_diff_editor_no_tools_planning_phase(registry):
    """plan_diff_editor exposes no tools in planning phase."""
    policy = registry.get("plan_diff_editor")
    tool_policy = policy["tool_policy"]
    planning_tools = tool_policy["allowed_tools_by_phase"].get("planning", [])
    assert planning_tools == [], (
        f"plan_diff_editor planning phase must have no tools, got {planning_tools}"
    )


def test_plan_diff_editor_no_browser_tools_any_phase(registry):
    policy = registry.get("plan_diff_editor")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & BROWSER_TOOLS
        assert not exposed, (
            f"plan_diff_editor phase={phase!r} must not expose browser tools: {exposed}"
        )


def test_plan_diff_editor_no_runtime_mutation_tools(registry):
    policy = registry.get("plan_diff_editor")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & RUNTIME_MUTATION_TOOLS
        assert not exposed, (
            f"plan_diff_editor phase={phase!r} must not expose runtime-mutation tools: {exposed}"
        )


def test_plan_diff_editor_context_policy_no_full_history(registry):
    """plan_diff_editor receives active plan context only — no full history."""
    policy = registry.get("plan_diff_editor")
    cp = policy["context_policy"]
    assert not cp.get("allow_full_history"), (
        "plan_diff_editor must not allow full history — active plan context only"
    )
    assert not cp.get("allow_unbounded_context"), (
        "plan_diff_editor must not allow unbounded context"
    )


def test_plan_diff_editor_context_policy_no_full_dom(registry):
    policy = registry.get("plan_diff_editor")
    cp = policy["context_policy"]
    assert not cp.get("allow_full_dom"), (
        "plan_diff_editor must not allow full DOM — active plan context only"
    )


def test_plan_diff_editor_has_validator_for_drop_prevention(registry):
    """plan_diff_editor must declare a validator (enforces cannot-drop policy)."""
    policy = registry.get("plan_diff_editor")
    assert policy["validator_id"], "plan_diff_editor must have a validator_id"
    assert policy["schema_id"], "plan_diff_editor must have a schema_id"


def test_plan_diff_editor_model_class_main(registry):
    policy = registry.get("plan_diff_editor")
    assert policy["model_class"] == "main"


def test_plan_diff_editor_schema_id(registry):
    policy = registry.get("plan_diff_editor")
    assert policy["schema_id"] == "plan_diff_editor.v1"


def test_plan_diff_editor_fallback_fail_closed(registry):
    policy = registry.get("plan_diff_editor")
    assert policy["fallback_policy"] == "fail_closed"


def test_plan_diff_editor_retry_fail_closed(registry):
    policy = registry.get("plan_diff_editor")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_plan_diff_editor_telemetry_fields(registry):
    policy = registry.get("plan_diff_editor")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status", "schema_id"}
    assert required <= set(tf.keys())


def test_plan_diff_editor_purpose_id(registry):
    policy = registry.get("plan_diff_editor")
    assert policy["purpose_id"] == "plan_diff_editor"


# ---------------------------------------------------------------------------
# custom_assertion_planner — inspection/context tools only
# ---------------------------------------------------------------------------

def test_custom_assertion_planner_no_browser_mutating_tools(registry):
    policy = registry.get("custom_assertion_planner")
    tool_policy = policy["tool_policy"]
    # Must not expose tools that mutate browser state
    mutating = {"action_click", "action_fill", "browser_navigate", "dom_mutate"}
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & mutating
        assert not exposed, (
            f"custom_assertion_planner phase={phase!r} must not expose mutating tools: {exposed}"
        )


def test_custom_assertion_planner_no_runtime_mutation_tools(registry):
    policy = registry.get("custom_assertion_planner")
    tool_policy = policy["tool_policy"]
    record_emit_tools = {"record_step", "emit_recorded", "emit_completed", "mark_done"}
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & record_emit_tools
        assert not exposed, (
            f"custom_assertion_planner phase={phase!r} must not expose record/emit tools: {exposed}"
        )


def test_custom_assertion_planner_has_ask_user_tool(registry):
    """custom_assertion_planner asks user when expected value is missing."""
    policy = registry.get("custom_assertion_planner")
    tool_policy = policy["tool_policy"]
    # ask_user must be available in at least one phase so user can be asked
    has_ask_user = any(
        "ask_user" in tools
        for tools in tool_policy["allowed_tools_by_phase"].values()
    )
    assert has_ask_user, "custom_assertion_planner must have ask_user tool available"


def test_custom_assertion_planner_uses_inspection_tools(registry):
    """custom_assertion_planner gets inspection/context tools (browser_get_state, dom_extract)."""
    policy = registry.get("custom_assertion_planner")
    tool_policy = policy["tool_policy"]
    inspection_tools = {"browser_get_state", "dom_extract", "locator_find", "locator_validate"}
    # At least one inspection tool must be available in planning phase
    planning_tools = set(tool_policy["allowed_tools_by_phase"].get("planning", []))
    has_inspection = bool(planning_tools & inspection_tools)
    assert has_inspection, (
        f"custom_assertion_planner must have inspection tools in planning phase, got {planning_tools}"
    )


def test_custom_assertion_planner_fallback_fail_closed(registry):
    """Unsupported assertion maps to capability_gap/fail-safe — fallback_policy must be fail_closed."""
    policy = registry.get("custom_assertion_planner")
    assert policy["fallback_policy"] == "fail_closed"


def test_custom_assertion_planner_retry_fail_closed(registry):
    """Invalid schema retries and fails closed."""
    policy = registry.get("custom_assertion_planner")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_custom_assertion_planner_model_class_main(registry):
    policy = registry.get("custom_assertion_planner")
    assert policy["model_class"] == "main"


def test_custom_assertion_planner_schema_id(registry):
    policy = registry.get("custom_assertion_planner")
    assert policy["schema_id"] == "custom_assertion_planner.v1"


def test_custom_assertion_planner_has_validator(registry):
    policy = registry.get("custom_assertion_planner")
    assert policy["validator_id"] == "schema_validator"


def test_custom_assertion_planner_telemetry_fields(registry):
    policy = registry.get("custom_assertion_planner")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status"}
    assert required <= set(tf.keys())


def test_custom_assertion_planner_purpose_id(registry):
    policy = registry.get("custom_assertion_planner")
    assert policy["purpose_id"] == "custom_assertion_planner"


def test_custom_assertion_planner_context_no_unbounded(registry):
    policy = registry.get("custom_assertion_planner")
    cp = policy["context_policy"]
    assert not cp.get("allow_unbounded_context")
    assert not cp.get("allow_full_history")


# ---------------------------------------------------------------------------
# Cross-purpose: all edit/assert purposes are fail-closed on schema failure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(EDIT_ASSERT_PURPOSES))
def test_edit_assert_purpose_retry_fail_closed(purpose, registry):
    policy = registry.get(purpose)
    rp = policy["retry_policy"]
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


@pytest.mark.parametrize("purpose", sorted(EDIT_ASSERT_PURPOSES))
def test_edit_assert_purpose_has_complete_metadata(purpose, registry):
    policy = registry.get(purpose)
    for field in ("purpose_id", "model_class", "context_policy", "skill_policy",
                  "tool_policy", "schema_id", "validator_id", "fallback_policy",
                  "retry_policy", "telemetry_fields"):
        assert field in policy, f"{purpose!r} missing field {field!r}"


# ---------------------------------------------------------------------------
# Singleton consistency
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(EDIT_ASSERT_PURPOSES))
def test_singleton_matches_factory(purpose):
    singleton = POLICY_REGISTRY.get(purpose)
    factory = build_default_registry().get(purpose)
    assert singleton["purpose_id"] == factory["purpose_id"]
    assert singleton["model_class"] == factory["model_class"]
    assert singleton["schema_id"] == factory["schema_id"]
    assert singleton["fallback_policy"] == factory["fallback_policy"]
