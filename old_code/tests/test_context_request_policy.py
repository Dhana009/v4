"""
tests/test_context_request_policy.py

Tests for S6-0203: Structured context request and escalation policy.
"""
from __future__ import annotations

import pytest
from runtime.context_request_policy import (
    PURPOSE_MAX_CONTEXT_LEVEL,
    EscalationLog,
    process_context_request,
)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_context_request_must_include_type_and_reason():
    with pytest.raises((ValueError, TypeError)):
        process_context_request("recovery_diagnoser", requested_type=None, reason=None, scope="error_element")


def test_context_request_rejects_unscoped_scope():
    result = process_context_request(
        "recovery_diagnoser",
        requested_type="L4",
        reason="need failure evidence",
        scope="",
    )
    assert result["approved"] is False
    assert "scope" in result["reason"].lower()


def test_context_request_rejects_escalation_beyond_purpose_max():
    # intent_classifier max is L0; requesting L3 should be denied
    # Use a specific scope so the ceiling check fires (not the scope check)
    result = process_context_request(
        "intent_classifier",
        requested_type="L3",
        reason="want more context",
        scope="login_button",
    )
    assert result["approved"] is False
    assert "exceed" in result["reason"].lower() or "max" in result["reason"].lower() or "l3" in result["reason"].lower()


def test_context_request_rejects_broad_full_dom_request():
    result = process_context_request(
        "recovery_diagnoser",
        requested_type="L5",
        reason="I want everything",
        scope="entire_page",
    )
    # L5 full DOM with broad scope should be denied (recovery_diagnoser max is L4)
    assert result["approved"] is False


def test_context_request_approves_scoped_escalation():
    # recovery_diagnoser can go up to L4
    result = process_context_request(
        "recovery_diagnoser",
        requested_type="L4",
        reason="need failure trace",
        scope="failing_element",
    )
    assert result["approved"] is True
    assert "escalated_context" in result or result.get("approved") is True


def test_approved_escalation_is_logged(monkeypatch):
    logged = []
    import runtime.context_request_policy as crp
    orig = crp._escalation_log.append if hasattr(crp._escalation_log, 'append') else None
    result = process_context_request(
        "recovery_diagnoser",
        requested_type="L4",
        reason="need failure trace",
        scope="failing_element",
    )
    assert result["approved"] is True
    log = EscalationLog.get_all()
    assert len(log) >= 1
    last = log[-1]
    assert last["approved"] is True


def test_denied_escalation_is_logged():
    result = process_context_request(
        "intent_classifier",
        requested_type="L3",
        reason="want more",
        scope="button",
    )
    assert result["approved"] is False
    log = EscalationLog.get_all()
    assert any(entry["approved"] is False for entry in log)


def test_fallback_issued_on_denial():
    result = process_context_request(
        "intent_classifier",
        requested_type="L3",
        reason="want more",
        scope="button",
    )
    assert result["approved"] is False
    assert "fallback" in result
    assert result["fallback"] == "ask_user"


def test_planning_purpose_cannot_escalate_to_l5():
    result = process_context_request(
        "journey_planner",
        requested_type="L5",
        reason="need full DOM",
        scope="full_page",
    )
    assert result["approved"] is False


def test_recovery_purpose_can_escalate_to_l4():
    result = process_context_request(
        "recovery_diagnoser",
        requested_type="L4",
        reason="need debug packet",
        scope="failing_step",
    )
    assert result["approved"] is True


def test_all_14_purposes_have_max_context_level():
    from runtime.llm_purpose_policy import REQUIRED_PURPOSE_IDS
    for pid in REQUIRED_PURPOSE_IDS:
        assert pid in PURPOSE_MAX_CONTEXT_LEVEL, f"Missing max level for {pid}"


def test_context_request_reason_required_not_empty():
    result = process_context_request(
        "recovery_diagnoser",
        requested_type="L4",
        reason="",
        scope="failing_element",
    )
    assert result["approved"] is False
