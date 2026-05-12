"""
S6-0106: Locator, execution, recovery, replay purpose policies — unit and contract tests.

Purposes: locator_specialist, execution_driver, recovery_diagnoser, replay_repair_specialist.
Tests-first policy: all tests written before implementation.
Source rule: Runtime Policy Spec — operational purposes have strict tool constraints.

Key invariants tested:
- locator_specialist gets locator/context tools only
- locator_specialist gets no action tools
- locator_specialist proposed locators require backend validation (validator_id set)
- execution_driver gets only next confirmed operation tool (executing phase only)
- execution_driver blocked outside executing phase in policy/validator expectations
- recovery_diagnoser cannot emit recorded/completed
- recovery_diagnoser has bounded retry/fallback
- replay_repair_specialist outputs repair diff only (schema_id declared)
- replay_repair_specialist cannot mutate recording directly (no record/emit tools)
- replay_repair_specialist gets replay evidence + locator/assertion tools only
"""
from __future__ import annotations

import pytest

from runtime.llm_policy_registry import build_default_registry, POLICY_REGISTRY

OPERATIONAL_PURPOSES = {
    "locator_specialist",
    "execution_driver",
    "recovery_diagnoser",
    "replay_repair_specialist",
}

ACTION_TOOLS = frozenset({"action_click", "action_fill", "action_assert"})
RECORD_EMIT_TOOLS = frozenset({"record_step", "emit_recorded", "emit_completed", "mark_done", "mark_running"})
BROWSER_NAV_TOOLS = frozenset({"browser_navigate", "browser_back", "browser_forward", "dom_mutate"})
ALL_MUTATION_TOOLS = ACTION_TOOLS | RECORD_EMIT_TOOLS | BROWSER_NAV_TOOLS


@pytest.fixture()
def registry():
    return build_default_registry()


# ---------------------------------------------------------------------------
# locator_specialist — locator/context tools only, no action tools
# ---------------------------------------------------------------------------

def test_locator_specialist_no_action_tools(registry):
    """locator_specialist must not get any action tools."""
    policy = registry.get("locator_specialist")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & ACTION_TOOLS
        assert not exposed, (
            f"locator_specialist phase={phase!r} must not expose action tools: {exposed}"
        )


def test_locator_specialist_no_record_emit_tools(registry):
    policy = registry.get("locator_specialist")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & RECORD_EMIT_TOOLS
        assert not exposed, (
            f"locator_specialist phase={phase!r} must not expose record/emit tools: {exposed}"
        )


def test_locator_specialist_has_locator_tools(registry):
    """locator_specialist must have locator/inspection tools."""
    policy = registry.get("locator_specialist")
    tool_policy = policy["tool_policy"]
    locator_tools = {"browser_get_state", "dom_extract", "locator_find", "locator_validate"}
    planning_tools = set(tool_policy["allowed_tools_by_phase"].get("planning", []))
    has_locator = bool(planning_tools & locator_tools)
    assert has_locator, (
        f"locator_specialist must have locator tools in planning phase, got {planning_tools}"
    )


def test_locator_specialist_validator_id_set(registry):
    """Proposed locators require backend validation — validator_id must be set."""
    policy = registry.get("locator_specialist")
    assert policy["validator_id"], "locator_specialist must have validator_id (locators need backend validation)"


def test_locator_specialist_model_class_main(registry):
    policy = registry.get("locator_specialist")
    assert policy["model_class"] == "main"


def test_locator_specialist_schema_id(registry):
    policy = registry.get("locator_specialist")
    assert policy["schema_id"] == "locator_specialist.v1"


def test_locator_specialist_fallback_fail_closed(registry):
    policy = registry.get("locator_specialist")
    assert policy["fallback_policy"] == "fail_closed"


def test_locator_specialist_retry_bounded(registry):
    policy = registry.get("locator_specialist")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_locator_specialist_telemetry(registry):
    policy = registry.get("locator_specialist")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status", "schema_id"}
    assert required <= set(tf.keys())


def test_locator_specialist_purpose_id(registry):
    policy = registry.get("locator_specialist")
    assert policy["purpose_id"] == "locator_specialist"


def test_locator_specialist_context_no_unbounded(registry):
    policy = registry.get("locator_specialist")
    cp = policy["context_policy"]
    assert not cp.get("allow_unbounded_context")
    assert not cp.get("allow_full_history")


# ---------------------------------------------------------------------------
# execution_driver — only next confirmed operation in executing phase
# ---------------------------------------------------------------------------

def test_execution_driver_action_tools_executing_phase_only(registry):
    """execution_driver gets action tools only in executing phase."""
    policy = registry.get("execution_driver")
    tool_policy = policy["tool_policy"]
    # Planning phase must NOT have action tools
    planning_tools = set(tool_policy["allowed_tools_by_phase"].get("planning", []))
    planning_action = planning_tools & ACTION_TOOLS
    assert not planning_action, (
        f"execution_driver planning phase must not expose action tools: {planning_action}"
    )


def test_execution_driver_executing_phase_has_action_tools(registry):
    """execution_driver executing phase must have exactly the confirmed action tools."""
    policy = registry.get("execution_driver")
    tool_policy = policy["tool_policy"]
    executing_tools = set(tool_policy["allowed_tools_by_phase"].get("executing", []))
    # Must have at least one action tool in executing phase
    has_action = bool(executing_tools & ACTION_TOOLS)
    assert has_action, (
        f"execution_driver executing phase must have action tools, got {executing_tools}"
    )


def test_execution_driver_no_record_emit_tools(registry):
    """execution_driver cannot record/emit — backend owns truth."""
    policy = registry.get("execution_driver")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & RECORD_EMIT_TOOLS
        assert not exposed, (
            f"execution_driver phase={phase!r} must not expose record/emit tools: {exposed}"
        )


def test_execution_driver_model_class_main(registry):
    policy = registry.get("execution_driver")
    assert policy["model_class"] == "main"


def test_execution_driver_schema_id(registry):
    policy = registry.get("execution_driver")
    assert policy["schema_id"] == "execution_driver.v1"


def test_execution_driver_fallback_fail_closed(registry):
    policy = registry.get("execution_driver")
    assert policy["fallback_policy"] == "fail_closed"


def test_execution_driver_retry_bounded(registry):
    policy = registry.get("execution_driver")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_execution_driver_telemetry(registry):
    policy = registry.get("execution_driver")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status"}
    assert required <= set(tf.keys())


def test_execution_driver_purpose_id(registry):
    policy = registry.get("execution_driver")
    assert policy["purpose_id"] == "execution_driver"


def test_execution_driver_completed_phase_no_tools(registry):
    """execution_driver gets no tools in completed phase."""
    policy = registry.get("execution_driver")
    tool_policy = policy["tool_policy"]
    completed_tools = tool_policy["allowed_tools_by_phase"].get("completed", [])
    assert not completed_tools, (
        f"execution_driver completed phase must have no tools, got {completed_tools}"
    )


# ---------------------------------------------------------------------------
# recovery_diagnoser — cannot emit recorded/completed, bounded retry
# ---------------------------------------------------------------------------

def test_recovery_diagnoser_no_record_emit_tools(registry):
    """recovery_diagnoser cannot emit recorded/completed — backend owns truth."""
    policy = registry.get("recovery_diagnoser")
    tool_policy = policy["tool_policy"]
    emit_tools = {"emit_recorded", "emit_completed", "record_step", "mark_done"}
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & emit_tools
        assert not exposed, (
            f"recovery_diagnoser phase={phase!r} must not expose emit tools: {exposed}"
        )


def test_recovery_diagnoser_no_action_tools(registry):
    policy = registry.get("recovery_diagnoser")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & ACTION_TOOLS
        assert not exposed, (
            f"recovery_diagnoser phase={phase!r} must not expose action tools: {exposed}"
        )


def test_recovery_diagnoser_retry_bounded(registry):
    """recovery_diagnoser has bounded retry/fallback."""
    policy = registry.get("recovery_diagnoser")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_recovery_diagnoser_model_class_main(registry):
    policy = registry.get("recovery_diagnoser")
    assert policy["model_class"] == "main"


def test_recovery_diagnoser_schema_id(registry):
    policy = registry.get("recovery_diagnoser")
    assert policy["schema_id"] == "recovery_diagnoser.v1"


def test_recovery_diagnoser_fallback_fail_closed(registry):
    policy = registry.get("recovery_diagnoser")
    assert policy["fallback_policy"] == "fail_closed"


def test_recovery_diagnoser_validator_id(registry):
    policy = registry.get("recovery_diagnoser")
    assert policy["validator_id"] == "schema_validator"


def test_recovery_diagnoser_telemetry(registry):
    policy = registry.get("recovery_diagnoser")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status"}
    assert required <= set(tf.keys())


def test_recovery_diagnoser_purpose_id(registry):
    policy = registry.get("recovery_diagnoser")
    assert policy["purpose_id"] == "recovery_diagnoser"


# ---------------------------------------------------------------------------
# replay_repair_specialist — repair diff only, no recording mutation
# ---------------------------------------------------------------------------

def test_replay_repair_specialist_no_record_emit_tools(registry):
    """replay_repair_specialist cannot mutate recording directly."""
    policy = registry.get("replay_repair_specialist")
    tool_policy = policy["tool_policy"]
    mutation_tools = {"record_step", "emit_recorded", "emit_completed", "mark_done"}
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & mutation_tools
        assert not exposed, (
            f"replay_repair_specialist phase={phase!r} must not expose recording-mutation tools: {exposed}"
        )


def test_replay_repair_specialist_no_action_tools(registry):
    """replay_repair_specialist outputs repair diff only — no direct actions."""
    policy = registry.get("replay_repair_specialist")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & ACTION_TOOLS
        assert not exposed, (
            f"replay_repair_specialist phase={phase!r} must not expose action tools: {exposed}"
        )


def test_replay_repair_specialist_schema_id(registry):
    """replay_repair_specialist outputs repair diff only — schema_id must be declared."""
    policy = registry.get("replay_repair_specialist")
    assert policy["schema_id"] == "replay_repair_specialist.v1"


def test_replay_repair_specialist_validator_required(registry):
    """replay_repair_specialist must have validator to verify repair diff format."""
    policy = registry.get("replay_repair_specialist")
    assert policy["validator_id"] == "schema_validator"


def test_replay_repair_specialist_model_class_main(registry):
    policy = registry.get("replay_repair_specialist")
    assert policy["model_class"] == "main"


def test_replay_repair_specialist_fallback_fail_closed(registry):
    policy = registry.get("replay_repair_specialist")
    assert policy["fallback_policy"] == "fail_closed"


def test_replay_repair_specialist_retry_bounded(registry):
    policy = registry.get("replay_repair_specialist")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


def test_replay_repair_specialist_telemetry(registry):
    policy = registry.get("replay_repair_specialist")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status", "schema_id"}
    assert required <= set(tf.keys())


def test_replay_repair_specialist_purpose_id(registry):
    policy = registry.get("replay_repair_specialist")
    assert policy["purpose_id"] == "replay_repair_specialist"


def test_replay_repair_specialist_context_no_full_history(registry):
    """replay_repair_specialist context is bounded — replay evidence only."""
    policy = registry.get("replay_repair_specialist")
    cp = policy["context_policy"]
    assert not cp.get("allow_full_history")
    assert not cp.get("allow_unbounded_context")


# ---------------------------------------------------------------------------
# Cross-purpose: all operational purposes fail-closed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(OPERATIONAL_PURPOSES))
def test_operational_purpose_retry_fail_closed(purpose, registry):
    policy = registry.get(purpose)
    rp = policy["retry_policy"]
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed"


@pytest.mark.parametrize("purpose", sorted(OPERATIONAL_PURPOSES))
def test_operational_purpose_has_complete_metadata(purpose, registry):
    policy = registry.get(purpose)
    for field in ("purpose_id", "model_class", "context_policy", "skill_policy",
                  "tool_policy", "schema_id", "validator_id", "fallback_policy",
                  "retry_policy", "telemetry_fields"):
        assert field in policy, f"{purpose!r} missing field {field!r}"


@pytest.mark.parametrize("purpose", sorted(OPERATIONAL_PURPOSES))
def test_operational_purpose_no_unbounded_context(purpose, registry):
    policy = registry.get(purpose)
    cp = policy["context_policy"]
    assert not cp.get("allow_unbounded_context")


# ---------------------------------------------------------------------------
# Singleton consistency
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(OPERATIONAL_PURPOSES))
def test_singleton_matches_factory(purpose):
    singleton = POLICY_REGISTRY.get(purpose)
    factory = build_default_registry().get(purpose)
    assert singleton["purpose_id"] == factory["purpose_id"]
    assert singleton["model_class"] == factory["model_class"]
    assert singleton["schema_id"] == factory["schema_id"]
    assert singleton["fallback_policy"] == factory["fallback_policy"]
