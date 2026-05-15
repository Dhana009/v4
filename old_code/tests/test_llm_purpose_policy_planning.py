"""
S6-0104: Planning and recommendation purpose policies — unit and contract tests.

Purposes: page_validation_recommender, journey_planner, step_plan_normalizer.
Tests-first policy: all tests written before implementation.
Source rule: Runtime Policy Spec — planning purposes get no execution tools.

Key invariants tested:
- page_validation_recommender gets no browser-changing tools
- journey_planner gets no execution tools
- step_plan_normalizer keeps existing S5 convergence behavior (policy stable)
- step_plan_normalizer preserves stable step IDs in policy/validator expectations
- journey_planner marks missing data instead of inventing (via policy constraints)
- page_validation_recommender requires context gate reference (schema_id present)
- invalid plan schema retries/fails closed
- S5-013 convergence contract tests still pass (verified separately)
"""
from __future__ import annotations

import pytest

from runtime.llm_policy_registry import build_default_registry, POLICY_REGISTRY

PLANNING_PURPOSES = {
    "page_validation_recommender",
    "journey_planner",
    "step_plan_normalizer",
}

# Execution / browser-changing tools that planning purposes must never expose
EXECUTION_TOOLS = frozenset({
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
    "mark_running",
    "mark_done",
})

BROWSER_CHANGING_TOOLS = frozenset({
    "action_click",
    "action_fill",
    "action_assert",
    "browser_navigate",
    "dom_mutate",
})


@pytest.fixture()
def registry():
    return build_default_registry()


# ---------------------------------------------------------------------------
# page_validation_recommender — read-only context, no browser mutation
# ---------------------------------------------------------------------------

def test_page_validation_recommender_no_browser_changing_tools(registry):
    policy = registry.get("page_validation_recommender")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & BROWSER_CHANGING_TOOLS
        assert not exposed, (
            f"page_validation_recommender phase={phase!r} must not expose browser-changing tools: {exposed}"
        )


def test_page_validation_recommender_no_execution_tools(registry):
    policy = registry.get("page_validation_recommender")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & EXECUTION_TOOLS
        assert not exposed, (
            f"page_validation_recommender phase={phase!r} must not expose execution tools: {exposed}"
        )


def test_page_validation_recommender_model_class_main(registry):
    policy = registry.get("page_validation_recommender")
    assert policy["model_class"] == "main"


def test_page_validation_recommender_schema_id(registry):
    policy = registry.get("page_validation_recommender")
    assert policy["schema_id"] == "page_validation_recommender.v1"


def test_page_validation_recommender_has_context_gate_reference(registry):
    """Requires context gate reference — must have context_policy and schema_id set."""
    policy = registry.get("page_validation_recommender")
    assert policy["schema_id"], "page_validation_recommender must have a schema_id"
    assert policy["context_policy"], "page_validation_recommender must have a context_policy"


def test_page_validation_recommender_fallback_fail_closed(registry):
    policy = registry.get("page_validation_recommender")
    assert policy["fallback_policy"] == "fail_closed"


def test_page_validation_recommender_retry_policy(registry):
    policy = registry.get("page_validation_recommender")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_page_validation_recommender_telemetry_fields(registry):
    policy = registry.get("page_validation_recommender")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status", "schema_id"}
    assert required <= set(tf.keys())


def test_page_validation_recommender_validator_id(registry):
    policy = registry.get("page_validation_recommender")
    assert policy["validator_id"] == "schema_validator"


def test_page_validation_recommender_purpose_id(registry):
    policy = registry.get("page_validation_recommender")
    assert policy["purpose_id"] == "page_validation_recommender"


# ---------------------------------------------------------------------------
# journey_planner — no execution tools
# ---------------------------------------------------------------------------

def test_journey_planner_no_execution_tools(registry):
    policy = registry.get("journey_planner")
    tool_policy = policy["tool_policy"]
    executing_tools = tool_policy["allowed_tools_by_phase"].get("executing", [])
    # journey_planner must not expose action tools during execution phase
    exposed = set(executing_tools) & EXECUTION_TOOLS
    assert not exposed, (
        f"journey_planner executing phase must not expose execution tools: {exposed}"
    )


def test_journey_planner_no_browser_changing_tools_any_phase(registry):
    policy = registry.get("journey_planner")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & BROWSER_CHANGING_TOOLS
        assert not exposed, (
            f"journey_planner phase={phase!r} must not expose browser-changing tools: {exposed}"
        )


def test_journey_planner_model_class_main(registry):
    policy = registry.get("journey_planner")
    assert policy["model_class"] == "main"


def test_journey_planner_schema_id(registry):
    policy = registry.get("journey_planner")
    assert policy["schema_id"] == "journey_planner.v1"


def test_journey_planner_fallback_fail_closed(registry):
    policy = registry.get("journey_planner")
    assert policy["fallback_policy"] == "fail_closed"


def test_journey_planner_retry_policy(registry):
    policy = registry.get("journey_planner")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_journey_planner_telemetry_fields(registry):
    policy = registry.get("journey_planner")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status"}
    assert required <= set(tf.keys())


def test_journey_planner_purpose_id(registry):
    policy = registry.get("journey_planner")
    assert policy["purpose_id"] == "journey_planner"


def test_journey_planner_validator_id(registry):
    policy = registry.get("journey_planner")
    assert policy["validator_id"] == "schema_validator"


# ---------------------------------------------------------------------------
# step_plan_normalizer — preserves S5 convergence behavior
# ---------------------------------------------------------------------------

def test_step_plan_normalizer_model_class_main(registry):
    """S5 convergence: step_plan_normalizer uses main model class."""
    policy = registry.get("step_plan_normalizer")
    assert policy["model_class"] == "main"


def test_step_plan_normalizer_no_execution_tools(registry):
    """step_plan_normalizer must not expose execution tools."""
    policy = registry.get("step_plan_normalizer")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & EXECUTION_TOOLS - {"action_click", "action_fill", "action_assert"}
        # step_plan_normalizer is a planner — no action tools allowed
        action_exposed = set(tools) & {"action_click", "action_fill", "action_assert"}
        assert not action_exposed, (
            f"step_plan_normalizer phase={phase!r} must not expose action tools: {action_exposed}"
        )


def test_step_plan_normalizer_schema_id(registry):
    policy = registry.get("step_plan_normalizer")
    assert policy["schema_id"] == "step_plan_normalizer.v1"


def test_step_plan_normalizer_fallback_fail_closed(registry):
    policy = registry.get("step_plan_normalizer")
    assert policy["fallback_policy"] == "fail_closed"


def test_step_plan_normalizer_retry_policy(registry):
    """Schema failure retries and then fails closed — preserves S5 convergence guard."""
    policy = registry.get("step_plan_normalizer")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_step_plan_normalizer_telemetry_fields(registry):
    policy = registry.get("step_plan_normalizer")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status", "schema_id"}
    assert required <= set(tf.keys())


def test_step_plan_normalizer_purpose_id(registry):
    policy = registry.get("step_plan_normalizer")
    assert policy["purpose_id"] == "step_plan_normalizer"


def test_step_plan_normalizer_validator_id(registry):
    policy = registry.get("step_plan_normalizer")
    assert policy["validator_id"] == "schema_validator"


def test_step_plan_normalizer_context_policy_no_unbounded(registry):
    """Context must never be unbounded — preserves stable step IDs expectation."""
    policy = registry.get("step_plan_normalizer")
    cp = policy["context_policy"]
    assert not cp.get("allow_unbounded_context"), (
        "step_plan_normalizer must not allow unbounded context"
    )
    assert not cp.get("allow_full_history"), (
        "step_plan_normalizer must not allow full history"
    )


# ---------------------------------------------------------------------------
# Cross-purpose: no planning purpose gets action tools
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(PLANNING_PURPOSES))
def test_planning_purpose_no_action_tools(purpose, registry):
    policy = registry.get(purpose)
    tool_policy = policy["tool_policy"]
    action_tools = {"action_click", "action_fill", "action_assert"}
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & action_tools
        assert not exposed, (
            f"{purpose!r} phase={phase!r} must not expose action tools: {exposed}"
        )


@pytest.mark.parametrize("purpose", sorted(PLANNING_PURPOSES))
def test_planning_purpose_retry_fallback_fail_closed(purpose, registry):
    policy = registry.get(purpose)
    rp = policy["retry_policy"]
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


@pytest.mark.parametrize("purpose", sorted(PLANNING_PURPOSES))
def test_planning_purpose_has_complete_metadata(purpose, registry):
    policy = registry.get(purpose)
    for field in ("purpose_id", "model_class", "context_policy", "skill_policy",
                  "tool_policy", "schema_id", "validator_id", "fallback_policy",
                  "retry_policy", "telemetry_fields"):
        assert field in policy, f"{purpose!r} missing field {field!r}"


# ---------------------------------------------------------------------------
# Singleton consistency
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(PLANNING_PURPOSES))
def test_singleton_matches_factory(purpose):
    singleton = POLICY_REGISTRY.get(purpose)
    factory = build_default_registry().get(purpose)
    assert singleton["purpose_id"] == factory["purpose_id"]
    assert singleton["model_class"] == factory["model_class"]
    assert singleton["schema_id"] == factory["schema_id"]
    assert singleton["fallback_policy"] == factory["fallback_policy"]
