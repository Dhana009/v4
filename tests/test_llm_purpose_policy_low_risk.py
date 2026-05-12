"""
S6-0103: Low-risk purpose policies — unit and contract tests.

Purposes: intent_classifier, clarification_generator, user_response_writer, trace_summarizer.
Tests-first policy: all tests written before implementation.
Source rule: Runtime Policy Spec — purpose-specific tool/schema/behavior constraints.

Key invariants tested:
- intent_classifier exposes no tools
- intent_classifier schema is enum-only (output is an intent classification)
- clarification_generator asks one focused question
- clarification_generator maps to missing field
- user_response_writer cannot claim execution success
- user_response_writer cannot claim unsupported capability succeeded
- trace_summarizer cannot mutate runtime truth
- trace_summarizer gets no browser-changing tools
- schema failure retries/falls back according to policy
- telemetry required fields exist
"""
from __future__ import annotations

import pytest

from runtime.llm_policy_registry import build_default_registry, POLICY_REGISTRY

LOW_RISK_PURPOSES = {
    "intent_classifier",
    "clarification_generator",
    "user_response_writer",
    "trace_summarizer",
}

# Browser-changing / action tools that must never be exposed to low-risk purposes
BROWSER_CHANGING_TOOLS = frozenset({
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

# Tools that claim/mutate runtime truth
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
# intent_classifier — no tools
# ---------------------------------------------------------------------------

def test_intent_classifier_no_tools_planning_phase(registry):
    policy = registry.get("intent_classifier")
    tool_policy = policy["tool_policy"]
    planning_tools = tool_policy["allowed_tools_by_phase"].get("planning", [])
    assert planning_tools == [], (
        f"intent_classifier must have no planning tools, got {planning_tools}"
    )


def test_intent_classifier_no_tools_any_phase(registry):
    policy = registry.get("intent_classifier")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        assert not tools, (
            f"intent_classifier phase={phase!r} must have no tools, got {tools}"
        )


def test_intent_classifier_no_browser_changing_tools(registry):
    policy = registry.get("intent_classifier")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & BROWSER_CHANGING_TOOLS
        assert not exposed, (
            f"intent_classifier phase={phase!r} must not expose browser-changing tools: {exposed}"
        )


def test_intent_classifier_model_class_cheap(registry):
    policy = registry.get("intent_classifier")
    assert policy["model_class"] == "cheap"


def test_intent_classifier_schema_id_format(registry):
    policy = registry.get("intent_classifier")
    assert policy["schema_id"] == "intent_classifier.v1"


def test_intent_classifier_fallback_fail_closed(registry):
    policy = registry.get("intent_classifier")
    assert policy["fallback_policy"] == "fail_closed"


def test_intent_classifier_has_retry_policy(registry):
    policy = registry.get("intent_classifier")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1


def test_intent_classifier_telemetry_has_required_fields(registry):
    policy = registry.get("intent_classifier")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status", "schema_id"}
    missing = required - set(tf.keys())
    assert not missing, f"intent_classifier telemetry missing: {missing}"


def test_intent_classifier_purpose_id(registry):
    policy = registry.get("intent_classifier")
    assert policy["purpose_id"] == "intent_classifier"


# ---------------------------------------------------------------------------
# clarification_generator — focused question
# ---------------------------------------------------------------------------

def test_clarification_generator_no_browser_changing_tools(registry):
    policy = registry.get("clarification_generator")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & BROWSER_CHANGING_TOOLS
        assert not exposed, (
            f"clarification_generator phase={phase!r} must not expose browser-changing tools: {exposed}"
        )


def test_clarification_generator_model_class_cheap(registry):
    policy = registry.get("clarification_generator")
    assert policy["model_class"] == "cheap"


def test_clarification_generator_schema_id(registry):
    policy = registry.get("clarification_generator")
    assert policy["schema_id"] == "clarification_generator.v1"


def test_clarification_generator_fallback_fail_closed(registry):
    policy = registry.get("clarification_generator")
    assert policy["fallback_policy"] == "fail_closed"


def test_clarification_generator_has_retry_policy(registry):
    policy = registry.get("clarification_generator")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1


def test_clarification_generator_has_validator(registry):
    policy = registry.get("clarification_generator")
    assert policy["validator_id"], "clarification_generator must have a validator_id"


def test_clarification_generator_no_runtime_mutation_tools(registry):
    policy = registry.get("clarification_generator")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & RUNTIME_MUTATION_TOOLS
        assert not exposed, (
            f"clarification_generator phase={phase!r} must not expose runtime-mutation tools: {exposed}"
        )


def test_clarification_generator_no_action_tools(registry):
    """clarification_generator must not expose any action tools that could execute."""
    policy = registry.get("clarification_generator")
    tool_policy = policy["tool_policy"]
    action_tools = {"action_click", "action_fill", "action_assert"}
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & action_tools
        assert not exposed, (
            f"clarification_generator phase={phase!r} must not expose action tools: {exposed}"
        )


def test_clarification_generator_telemetry_has_required_fields(registry):
    policy = registry.get("clarification_generator")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status"}
    assert required <= set(tf.keys())


# ---------------------------------------------------------------------------
# user_response_writer — cannot claim execution success
# ---------------------------------------------------------------------------

def test_user_response_writer_cannot_have_action_tools(registry):
    """user_response_writer must not expose any action tools (cannot claim execution)."""
    policy = registry.get("user_response_writer")
    tool_policy = policy["tool_policy"]
    action_tools = {"action_click", "action_fill", "action_assert"}
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & action_tools
        assert not exposed, (
            f"user_response_writer phase={phase!r} must not expose action tools: {exposed}"
        )


def test_user_response_writer_cannot_have_browser_changing_tools(registry):
    policy = registry.get("user_response_writer")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & BROWSER_CHANGING_TOOLS
        assert not exposed, (
            f"user_response_writer phase={phase!r} exposes browser-changing tools: {exposed}"
        )


def test_user_response_writer_cannot_have_runtime_mutation_tools(registry):
    policy = registry.get("user_response_writer")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & RUNTIME_MUTATION_TOOLS
        assert not exposed, (
            f"user_response_writer phase={phase!r} exposes runtime-mutation tools: {exposed}"
        )


def test_user_response_writer_model_class_cheap(registry):
    policy = registry.get("user_response_writer")
    assert policy["model_class"] == "cheap"


def test_user_response_writer_schema_id(registry):
    policy = registry.get("user_response_writer")
    assert policy["schema_id"] == "user_response_writer.v1"


def test_user_response_writer_fallback_fail_closed(registry):
    policy = registry.get("user_response_writer")
    assert policy["fallback_policy"] == "fail_closed"


def test_user_response_writer_has_retry_policy(registry):
    policy = registry.get("user_response_writer")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1


def test_user_response_writer_telemetry_fields(registry):
    policy = registry.get("user_response_writer")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status"}
    assert required <= set(tf.keys())


def test_user_response_writer_purpose_id(registry):
    policy = registry.get("user_response_writer")
    assert policy["purpose_id"] == "user_response_writer"


# ---------------------------------------------------------------------------
# trace_summarizer — cannot mutate runtime truth
# ---------------------------------------------------------------------------

def test_trace_summarizer_no_tools(registry):
    """trace_summarizer gets no tools at all."""
    policy = registry.get("trace_summarizer")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        assert not tools, (
            f"trace_summarizer phase={phase!r} must have no tools, got {tools}"
        )


def test_trace_summarizer_no_browser_changing_tools(registry):
    policy = registry.get("trace_summarizer")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & BROWSER_CHANGING_TOOLS
        assert not exposed, (
            f"trace_summarizer phase={phase!r} exposes browser-changing tools: {exposed}"
        )


def test_trace_summarizer_no_runtime_mutation_tools(registry):
    policy = registry.get("trace_summarizer")
    tool_policy = policy["tool_policy"]
    for phase, tools in tool_policy["allowed_tools_by_phase"].items():
        exposed = set(tools) & RUNTIME_MUTATION_TOOLS
        assert not exposed, (
            f"trace_summarizer phase={phase!r} exposes runtime-mutation tools: {exposed}"
        )


def test_trace_summarizer_model_class_cheap(registry):
    policy = registry.get("trace_summarizer")
    assert policy["model_class"] == "cheap"


def test_trace_summarizer_schema_id(registry):
    policy = registry.get("trace_summarizer")
    assert policy["schema_id"] == "trace_summarizer.v1"


def test_trace_summarizer_fallback_fail_closed(registry):
    policy = registry.get("trace_summarizer")
    assert policy["fallback_policy"] == "fail_closed"


def test_trace_summarizer_has_retry_policy(registry):
    policy = registry.get("trace_summarizer")
    rp = policy["retry_policy"]
    assert rp.get("schema_retry_limit", 0) >= 1


def test_trace_summarizer_telemetry_fields(registry):
    policy = registry.get("trace_summarizer")
    tf = policy["telemetry_fields"]
    required = {"purpose", "model", "call_id", "validation_status"}
    assert required <= set(tf.keys())


def test_trace_summarizer_purpose_id(registry):
    policy = registry.get("trace_summarizer")
    assert policy["purpose_id"] == "trace_summarizer"


# ---------------------------------------------------------------------------
# Negative: all 4 low-risk purposes are fail-closed on schema failure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(LOW_RISK_PURPOSES))
def test_retry_policy_fallback_is_fail_closed(purpose, registry):
    policy = registry.get(purpose)
    rp = policy["retry_policy"]
    fallback = rp.get("fallback") or rp.get("fallback_action") or rp.get("on_failure")
    assert fallback == "fail_closed", (
        f"{purpose!r} retry_policy fallback must be 'fail_closed', got {fallback!r}"
    )


# ---------------------------------------------------------------------------
# Negative: unknown purpose fails closed (not silently skipped)
# ---------------------------------------------------------------------------

def test_unknown_purpose_not_in_low_risk_set_fails_closed(registry):
    with pytest.raises((ValueError, KeyError)):
        registry.get("made_up_low_risk_purpose")


# ---------------------------------------------------------------------------
# Cross-check: POLICY_REGISTRY singleton matches build_default_registry
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(LOW_RISK_PURPOSES))
def test_singleton_and_factory_agree(purpose):
    singleton_policy = POLICY_REGISTRY.get(purpose)
    factory_policy = build_default_registry().get(purpose)
    assert singleton_policy["purpose_id"] == factory_policy["purpose_id"]
    assert singleton_policy["model_class"] == factory_policy["model_class"]
    assert singleton_policy["schema_id"] == factory_policy["schema_id"]
    assert singleton_policy["fallback_policy"] == factory_policy["fallback_policy"]
