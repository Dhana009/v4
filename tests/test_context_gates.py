"""
tests/test_context_gates.py

Tests for S6-0202: Context sufficiency gates.
Verifies gate logic for each purpose family.
"""
from __future__ import annotations

import pytest
from runtime.context_gates import (
    GATE_CLARIFICATIONS,
    SUFFICIENCY_GATES,
    GateResult,
    check_gates,
)


def _ctx(**kwargs):
    """Build a minimal context dict for gate testing."""
    return kwargs


# ---------------------------------------------------------------------------
# Unit tests: individual gates
# ---------------------------------------------------------------------------

def test_intent_gate_passes_if_goal_clear():
    ctx = _ctx(user_goal="Click the login button")
    result = check_gates("intent_classifier", ctx)
    assert result.passed is True


def test_intent_gate_fails_if_ambiguous():
    ctx = _ctx(user_goal=None)
    result = check_gates("intent_classifier", ctx)
    assert result.passed is False
    assert result.failed_gate is not None


def test_intent_gate_fails_if_empty_goal():
    ctx = _ctx(user_goal="")
    result = check_gates("intent_classifier", ctx)
    assert result.passed is False


def test_page_recommendation_gate_requires_page_state():
    ctx = _ctx(page_state=None, page_intelligence=None)
    result = check_gates("page_validation_recommender", ctx)
    assert result.passed is False


def test_page_recommendation_gate_passes_with_state_and_intelligence():
    ctx = _ctx(page_state={"url": "https://example.com"}, page_intelligence={"headings": []})
    result = check_gates("page_validation_recommender", ctx)
    assert result.passed is True


def test_journey_planning_gate_requires_pages_list():
    ctx = _ctx(target_pages=None)
    result = check_gates("journey_planner", ctx)
    assert result.passed is False


def test_journey_planning_gate_passes_with_pages():
    ctx = _ctx(target_pages=["login", "dashboard"])
    result = check_gates("journey_planner", ctx)
    assert result.passed is True


def test_step_planning_gate_requires_step_ids():
    ctx = _ctx(step_ids=None, page_state={"url": "x"})
    result = check_gates("step_plan_normalizer", ctx)
    assert result.passed is False


def test_step_planning_gate_passes_with_step_ids_and_page_state():
    ctx = _ctx(step_ids=["s1", "s2"], page_state={"url": "x"})
    result = check_gates("step_plan_normalizer", ctx)
    assert result.passed is True


def test_locator_gate_requires_validation_result():
    ctx = _ctx(validation_result=None)
    result = check_gates("locator_specialist", ctx)
    assert result.passed is False


def test_locator_gate_passes_with_validation_result():
    ctx = _ctx(validation_result={"target": "button#submit"})
    result = check_gates("locator_specialist", ctx)
    assert result.passed is True


def test_recovery_gate_requires_failure_evidence():
    ctx = _ctx(failure_evidence=None)
    result = check_gates("recovery_diagnoser", ctx)
    assert result.passed is False


def test_recovery_gate_passes_with_failure_evidence():
    ctx = _ctx(failure_evidence={"error": "TimeoutError", "step": "click"})
    result = check_gates("recovery_diagnoser", ctx)
    assert result.passed is True


def test_failed_gate_returns_clarification_request():
    ctx = _ctx(user_goal=None)
    result = check_gates("intent_classifier", ctx)
    assert result.passed is False
    assert result.clarification_message is not None
    assert len(result.clarification_message) > 0


def test_gate_result_is_typed():
    ctx = _ctx(user_goal="test")
    result = check_gates("intent_classifier", ctx)
    assert isinstance(result, GateResult)
    assert isinstance(result.passed, bool)


def test_purpose_without_gates_passes_by_default():
    """Purposes with no explicit gates should pass (no gates = no blocker)."""
    ctx = _ctx()
    result = check_gates("user_response_writer", ctx)
    assert result.passed is True


def test_gate_clarifications_cover_all_gate_names():
    """Every gate name used in SUFFICIENCY_GATES must have a clarification."""
    for _purpose, gates in SUFFICIENCY_GATES.items():
        for gate_name, _fn in gates:
            assert gate_name in GATE_CLARIFICATIONS, f"No clarification for gate '{gate_name}'"


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_failed_gate_emits_ask_user():
    ctx = _ctx(user_goal=None)
    result = check_gates("intent_classifier", ctx)
    assert result.passed is False
    assert result.action == "ask_user"


def test_all_purpose_families_have_gates():
    expected_purposes = {
        "intent_classifier",
        "page_validation_recommender",
        "journey_planner",
        "step_plan_normalizer",
        "locator_specialist",
        "recovery_diagnoser",
    }
    for pid in expected_purposes:
        assert pid in SUFFICIENCY_GATES, f"No gates for {pid}"
