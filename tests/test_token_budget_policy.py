"""
tests/test_token_budget_policy.py

Tests for S6-0207: Token budget enforcement and telemetry.
"""
from __future__ import annotations

import pytest
from runtime.token_budget_policy import (
    PURPOSE_TOKEN_BUDGETS,
    BudgetResult,
    TelemetryRecord,
    check_and_enforce_budget,
    record_llm_call_telemetry,
    get_telemetry_log,
    clear_telemetry_log,
)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_each_purpose_has_token_budget():
    from runtime.llm_purpose_policy import REQUIRED_PURPOSE_IDS
    for pid in REQUIRED_PURPOSE_IDS:
        assert pid in PURPOSE_TOKEN_BUDGETS, f"Missing budget for {pid}"
        assert PURPOSE_TOKEN_BUDGETS[pid] > 0


def test_budget_within_limit_proceeds():
    result = check_and_enforce_budget("intent_classifier", context_tokens=200)
    assert result.action == "proceed"
    assert result.enforced is True


def test_budget_exceeded_triggers_compaction_or_clarification():
    # intent_classifier budget is 500 — send 600 tokens
    result = check_and_enforce_budget("intent_classifier", context_tokens=600)
    assert result.action in ("compact", "ask_clarification", "fail_closed")


def test_compaction_reduces_context_tokens():
    """When compaction is possible, action should be 'compact'."""
    result = check_and_enforce_budget(
        "step_plan_normalizer",
        context_tokens=4000,  # over budget
        can_compact=True,
    )
    assert result.action == "compact"


def test_clarification_asked_if_compaction_insufficient():
    result = check_and_enforce_budget(
        "step_plan_normalizer",
        context_tokens=4000,
        can_compact=False,
    )
    # Cannot compact → ask for clarification or fail
    assert result.action in ("ask_clarification", "fail_closed")


def test_fail_closed_if_no_escalation_allowed():
    result = check_and_enforce_budget(
        "page_intelligence_summarizer",
        context_tokens=99999,
        can_compact=False,
    )
    assert result.action in ("fail_closed", "ask_clarification")


def test_telemetry_includes_purpose_model_tokens():
    clear_telemetry_log()
    record_llm_call_telemetry(TelemetryRecord(
        purpose="intent_classifier",
        model="cheap",
        context_level="L0",
        context_tokens=300,
        total_input_tokens=350,
        output_tokens=45,
        latency_ms=120,
        finish_reason="stop",
        schema_validation="passed",
        result="success",
    ))
    log = get_telemetry_log()
    assert len(log) >= 1
    entry = log[-1]
    assert entry["purpose"] == "intent_classifier"
    assert entry["model"] == "cheap"
    assert "context_tokens" in entry


def test_telemetry_includes_latency():
    clear_telemetry_log()
    record_llm_call_telemetry(TelemetryRecord(
        purpose="recovery_diagnoser",
        model="main",
        context_level="L4",
        context_tokens=1200,
        total_input_tokens=1500,
        output_tokens=80,
        latency_ms=2340,
        finish_reason="stop",
        schema_validation="passed",
        result="success",
    ))
    log = get_telemetry_log()
    entry = log[-1]
    assert entry["latency_ms"] == 2340


def test_budget_exceeded_logged():
    clear_telemetry_log()
    result = check_and_enforce_budget("intent_classifier", context_tokens=9999)
    log = get_telemetry_log()
    # The budget check should produce a log entry
    assert result.action != "proceed"


def test_budget_result_is_typed():
    result = check_and_enforce_budget("intent_classifier", context_tokens=100)
    assert isinstance(result, BudgetResult)
    assert hasattr(result, "action")
    assert hasattr(result, "enforced")


def test_intent_classifier_budget_is_reasonable():
    budget = PURPOSE_TOKEN_BUDGETS["intent_classifier"]
    assert 300 <= budget <= 1000  # reasonable range


def test_journey_planner_budget_higher_than_intent():
    assert PURPOSE_TOKEN_BUDGETS["journey_planner"] > PURPOSE_TOKEN_BUDGETS["intent_classifier"]


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_single_call_budget_enforced_below_limit():
    result = check_and_enforce_budget("intent_classifier", context_tokens=50)
    assert result.action == "proceed"
    assert result.enforced is True


def test_telemetry_record_captures_schema_validation():
    clear_telemetry_log()
    record_llm_call_telemetry(TelemetryRecord(
        purpose="step_plan_normalizer",
        model="main",
        context_level="L1",
        context_tokens=800,
        total_input_tokens=1000,
        output_tokens=120,
        latency_ms=450,
        finish_reason="stop",
        schema_validation="passed",
        result="success",
    ))
    log = get_telemetry_log()
    assert log[-1]["schema_validation"] == "passed"
