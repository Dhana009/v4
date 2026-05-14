"""
E4 — execution lifecycle event contracts.

Plan ref: .tasks-md/Planning/S7-CROSS-LAYER-COMPLETION-PLAN.md Backend
Seams B8 (execution_started / operation_executed / operation_failed),
B9 (precondition_failed), B10 (locator_update_request / applied) and
the step_failed / step_skipped enrichments.

Tests pin schema + redaction before wiring or extending builders.
Sprint 7 ships builders + frontend; broad backend emission is deferred
to follow-up batches per plan rule "no fake lifecycle events" — the
existing emission sites are enriched rather than duplicated.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_execution_started_event,
    build_locator_update_applied_event,
    build_locator_update_request_event,
    build_operation_executed_event,
    build_operation_failed_event,
    build_precondition_failed_event,
    build_step_failed_payload,
    build_step_skipped_payload,
)


# --------------------------------------------------------------------------- #
# execution_started
# --------------------------------------------------------------------------- #
def test_execution_started_minimal_shape():
    event = build_execution_started_event(run_id="run-1", step_count=3)
    assert event["type"] == "execution_started"
    assert event["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    payload = event["payload"]
    assert payload["run_id"] == "run-1"
    assert payload["step_count"] == 3
    assert payload["source"] == "confirmed_plan"  # default
    assert event.get("event_id")
    assert event.get("emitted_at")


@pytest.mark.parametrize(
    "source", ["confirmed_plan", "deterministic", "replay", "unknown"]
)
def test_execution_started_accepts_known_sources(source):
    event = build_execution_started_event(run_id="r", step_count=1, source=source)
    assert event["payload"]["source"] == source


def test_execution_started_rejects_unknown_source():
    with pytest.raises(ValueError):
        build_execution_started_event(run_id="r", step_count=1, source="bogus")


def test_execution_started_carries_plan_id_when_provided():
    event = build_execution_started_event(run_id="r", step_count=2, plan_id="plan-x")
    assert event["payload"]["plan_id"] == "plan-x"


def test_execution_started_step_count_must_be_non_negative():
    with pytest.raises(ValueError):
        build_execution_started_event(run_id="r", step_count=-1)


# --------------------------------------------------------------------------- #
# operation_executed
# --------------------------------------------------------------------------- #
def test_operation_executed_minimal_shape():
    event = build_operation_executed_event(
        run_id="r",
        step_id="s1",
        operation_id="op_0",
        action="click",
    )
    payload = event["payload"]
    assert event["type"] == "operation_executed"
    assert payload["status"] == "passed"
    assert payload["action"] == "click"
    assert payload["operation_id"] == "op_0"


def test_operation_executed_strips_secret_shaped_fields_from_evidence():
    """B8 / S-matrix: result_summary must never carry a secret VALUE.
    Keys are preserved (debuggability), values are replaced with the
    redaction sentinel via the shared redact_payload helper.
    """
    event = build_operation_executed_event(
        run_id="r",
        step_id="s1",
        operation_id="op_0",
        action="fill",
        result_summary={"value": "[REDACTED]", "api_key": "sk-leak", "token": "ghp_leak"},
        locator="[data-test='username']",
    )
    summary = event["payload"]["result_summary"]
    assert summary["api_key"] == "[REDACTED]"
    assert summary["token"] == "[REDACTED]"
    assert summary["value"] == "[REDACTED]"
    assert event["payload"]["locator"] == "[data-test='username']"


def test_operation_executed_caps_result_summary_string_length():
    """B8: cap loose summary strings to 500 chars."""
    event = build_operation_executed_event(
        run_id="r",
        step_id="s1",
        operation_id="op_0",
        action="assert_text",
        result_summary="x" * 10_000,
    )
    assert len(event["payload"]["result_summary"]) <= 500


def test_operation_executed_rejects_blank_operation_id():
    """B8 root-cause guard: operation_id MUST never be empty."""
    with pytest.raises(ValueError):
        build_operation_executed_event(
            run_id="r", step_id="s1", operation_id="", action="click"
        )


# --------------------------------------------------------------------------- #
# operation_failed
# --------------------------------------------------------------------------- #
def test_operation_failed_minimal_shape():
    event = build_operation_failed_event(
        run_id="r",
        step_id="s1",
        operation_id="op_0",
        action="click",
        error_summary="locator not found",
    )
    payload = event["payload"]
    assert event["type"] == "operation_failed"
    assert payload["recoverable"] is True  # default
    assert payload["error_summary"] == "locator not found"


def test_operation_failed_redacts_error_summary_secrets():
    event = build_operation_failed_event(
        run_id="r",
        step_id="s1",
        operation_id="op_0",
        action="fill",
        error_summary="Error: token=ghp_leak failed at sk-leak1234567890",
    )
    summary = event["payload"]["error_summary"]
    assert "sk-leak1234567890" not in summary
    assert "ghp_leak" not in summary


def test_operation_failed_carries_retry_metadata_when_provided():
    event = build_operation_failed_event(
        run_id="r",
        step_id="s1",
        operation_id="op_0",
        action="click",
        error_summary="timeout",
        recoverable=False,
        retry_count=2,
        max_retries=3,
    )
    payload = event["payload"]
    assert payload["recoverable"] is False
    assert payload["retry_count"] == 2
    assert payload["max_retries"] == 3


# --------------------------------------------------------------------------- #
# precondition_failed
# --------------------------------------------------------------------------- #
def test_precondition_failed_minimal_shape():
    event = build_precondition_failed_event(
        run_id="r",
        step_id="s1",
        precondition_type="page_url",
        expected="https://example.com/dashboard",
        actual="https://example.com/login",
    )
    payload = event["payload"]
    assert event["type"] == "precondition_failed"
    assert payload["precondition_type"] == "page_url"
    # Default option set
    assert any(opt["id"] == "navigate" for opt in payload["options"])


def test_precondition_failed_caps_expected_and_actual_length():
    event = build_precondition_failed_event(
        run_id="r",
        step_id="s1",
        precondition_type="page_url",
        expected="x" * 1000,
        actual="y" * 1000,
    )
    payload = event["payload"]
    assert len(payload["expected"]) <= 300
    assert len(payload["actual"]) <= 300


def test_precondition_failed_strips_url_query_secret_patterns():
    """B9 / S-matrix: URL with token= must not survive emission."""
    event = build_precondition_failed_event(
        run_id="r",
        step_id="s1",
        precondition_type="page_url",
        expected="https://example.com/page",
        actual="https://example.com/page?token=ghp_leakymctoken123456&other=ok",
    )
    actual = event["payload"]["actual"]
    assert "ghp_leakymctoken123456" not in actual


@pytest.mark.parametrize(
    "ptype", ["page_url", "element_present", "auth_state", "data_ready"]
)
def test_precondition_failed_accepts_known_types(ptype):
    event = build_precondition_failed_event(
        run_id="r", step_id="s1", precondition_type=ptype, expected="a", actual="b"
    )
    assert event["payload"]["precondition_type"] == ptype


def test_precondition_failed_rejects_unknown_type():
    with pytest.raises(ValueError):
        build_precondition_failed_event(
            run_id="r",
            step_id="s1",
            precondition_type="bogus",
            expected="a",
            actual="b",
        )


# --------------------------------------------------------------------------- #
# locator_update_request / locator_update_applied
# --------------------------------------------------------------------------- #
def test_locator_update_request_minimal_shape():
    event = build_locator_update_request_event(
        run_id="r",
        step_id="s1",
        ambiguity_id="amb-1",
        current_locator="[data-test='x']",
        trigger="user",
    )
    payload = event["payload"]
    assert event["type"] == "locator_update_request"
    assert payload["trigger"] == "user"


@pytest.mark.parametrize("trigger", ["user", "weak_score", "failure_recovery"])
def test_locator_update_request_accepts_known_triggers(trigger):
    event = build_locator_update_request_event(
        run_id="r",
        step_id="s1",
        ambiguity_id="amb-1",
        current_locator="[x]",
        trigger=trigger,
    )
    assert event["payload"]["trigger"] == trigger


def test_locator_update_request_rejects_oversized_locator():
    with pytest.raises(ValueError):
        build_locator_update_request_event(
            run_id="r",
            step_id="s1",
            ambiguity_id="amb-1",
            current_locator="x" * 2000,
            trigger="user",
        )


def test_locator_update_applied_carries_old_and_new_locator():
    event = build_locator_update_applied_event(
        run_id="r",
        step_id="s1",
        ambiguity_id="amb-1",
        old_locator="[a]",
        new_locator="[b]",
        strategy="user_pick",
        confidence=0.92,
    )
    payload = event["payload"]
    assert payload["old_locator"] == "[a]"
    assert payload["new_locator"] == "[b]"
    assert payload["strategy"] == "user_pick"
    assert payload["confidence"] == 0.92


def test_locator_update_applied_rejects_unknown_strategy():
    with pytest.raises(ValueError):
        build_locator_update_applied_event(
            run_id="r",
            step_id="s1",
            ambiguity_id="amb-1",
            old_locator="[a]",
            new_locator="[b]",
            strategy="wishful_thinking",
            confidence=0.5,
        )


# --------------------------------------------------------------------------- #
# Existing step_failed / step_skipped — backward-compatible enrichments
# --------------------------------------------------------------------------- #
def test_step_failed_accepts_recovery_metadata_optional_fields():
    """E4 extends the existing builder with optional resilience fields."""
    event = build_step_failed_payload(
        step_id="s1",
        run_id="r",
        error="timeout",
        status="failed",
        recovery_available=True,
        next_safe_actions=["retry", "skip"],
    )
    payload = event["payload"]
    assert payload["recovery_available"] is True
    assert payload["next_safe_actions"] == ["retry", "skip"]


def test_step_failed_legacy_call_still_works_without_new_fields():
    event = build_step_failed_payload(
        step_id="s1", run_id="r", error="timeout", status="failed"
    )
    payload = event["payload"]
    # Legacy callers must not see the new optional fields injected.
    assert "recovery_available" not in payload
    assert "next_safe_actions" not in payload


def test_step_skipped_accepts_skipped_by_and_remaining_count():
    event = build_step_skipped_payload(
        step_id="s1",
        run_id="r",
        reason="user requested",
        skipped_by="user",
        remaining_step_count=2,
    )
    payload = event["payload"]
    assert payload["skipped_by"] == "user"
    assert payload["remaining_step_count"] == 2


@pytest.mark.parametrize("by", ["user", "backend", "recovery", "unknown"])
def test_step_skipped_accepts_known_skipped_by_values(by):
    event = build_step_skipped_payload(
        step_id="s1", run_id="r", reason="x", skipped_by=by
    )
    assert event["payload"]["skipped_by"] == by


def test_step_skipped_rejects_unknown_skipped_by_value():
    with pytest.raises(ValueError):
        build_step_skipped_payload(
            step_id="s1", run_id="r", reason="x", skipped_by="bogus"
        )
