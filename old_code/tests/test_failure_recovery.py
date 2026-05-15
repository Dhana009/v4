"""
tests/test_failure_recovery.py

Tests for Cluster 8: Recovery + Failure Handling + Execution Safety.
S6-0801 through S6-0809.
"""
from __future__ import annotations

import pytest
from runtime.failure_classifier import (
    FailureType,
    FailureClassification,
    classify_failure,
)
from runtime.recovery_pipeline import (
    RecoveryPacket,
    RecoveryProposal,
    RecoveryLifecycleState,
    RecoveryStatus,
    build_recovery_packet,
    propose_deterministic_recovery,
    can_complete_after_recovery,
    can_record_after_recovery,
)


# ---------------------------------------------------------------------------
# S6-0801: Failure Classification Pipeline
# ---------------------------------------------------------------------------

def test_element_not_found_classified_correctly():
    result = classify_failure({"error": "ElementNotFoundError", "step": "click_submit"})
    assert result.failure_type == FailureType.ELEMENT_NOT_FOUND


def test_timeout_classified_correctly():
    result = classify_failure({"error": "TimeoutError", "step": "wait_for_nav"})
    assert result.failure_type == FailureType.TIMEOUT


def test_network_error_classified():
    result = classify_failure({"error": "NetworkError: fetch failed", "step": "navigate"})
    assert result.failure_type == FailureType.NETWORK_ERROR


def test_assertion_failure_classified():
    result = classify_failure({"error": "AssertionError: expected 'Login' got 'Sign In'", "step": "assert_text"})
    assert result.failure_type == FailureType.ASSERTION_FAILURE


def test_unknown_failure_classified_as_unknown():
    result = classify_failure({"error": "Something completely bizarre happened"})
    assert result.failure_type == FailureType.UNKNOWN


def test_failure_classification_is_typed():
    result = classify_failure({"error": "TimeoutError"})
    assert isinstance(result, FailureClassification)
    assert hasattr(result, "failure_type")
    assert hasattr(result, "is_recoverable")


# ---------------------------------------------------------------------------
# S6-0802: Deterministic Recovery First
# ---------------------------------------------------------------------------

def test_deterministic_recovery_proposed_before_llm():
    packet = RecoveryPacket(
        step_id="s1",
        failure_type=FailureType.ELEMENT_NOT_FOUND,
        error_message="ElementNotFoundError",
        failed_locator="[data-testid=submit]",
        page_url="https://example.com",
    )
    proposal = propose_deterministic_recovery(packet)
    assert proposal is not None
    assert proposal.strategy in ("retry_locator", "wait_and_retry", "ask_user", "fail_closed")


def test_deterministic_recovery_for_timeout_is_wait_retry():
    packet = RecoveryPacket(
        step_id="s1",
        failure_type=FailureType.TIMEOUT,
        error_message="TimeoutError",
        failed_locator=None,
        page_url="https://example.com",
    )
    proposal = propose_deterministic_recovery(packet)
    assert proposal.strategy in ("wait_and_retry", "ask_user")


# ---------------------------------------------------------------------------
# S6-0803: Recovery Context Packet
# ---------------------------------------------------------------------------

def test_build_recovery_packet_from_failure():
    packet = build_recovery_packet(
        step_id="s2",
        error={"error": "ElementNotFoundError", "step": "s2"},
        page_url="https://example.com/login",
        failed_locator="[data-testid=username]",
    )
    assert isinstance(packet, RecoveryPacket)
    assert packet.step_id == "s2"
    assert packet.page_url == "https://example.com/login"
    assert packet.failed_locator == "[data-testid=username]"


def test_recovery_packet_has_failure_type():
    packet = build_recovery_packet(
        step_id="s1",
        error={"error": "TimeoutError"},
        page_url="https://example.com",
        failed_locator=None,
    )
    assert packet.failure_type is not None


# ---------------------------------------------------------------------------
# S6-0804: Recovery Diagnoser Repair Proposal Schema
# ---------------------------------------------------------------------------

def test_recovery_proposal_has_required_fields():
    proposal = RecoveryProposal(
        strategy="retry_locator",
        proposed_locator="[aria-label=Submit]",
        confidence=0.8,
        reason="alternative locator found",
    )
    assert proposal.strategy is not None
    assert proposal.confidence >= 0


# ---------------------------------------------------------------------------
# S6-0805: Recovery State Lifecycle
# ---------------------------------------------------------------------------

def test_recovery_state_blocks_completion():
    state = RecoveryLifecycleState(step_id="s1")
    state.enter_recovery(FailureType.ELEMENT_NOT_FOUND)
    assert can_complete_after_recovery(state) is False


def test_recovery_state_blocks_recording():
    state = RecoveryLifecycleState(step_id="s1")
    state.enter_recovery(FailureType.TIMEOUT)
    assert can_record_after_recovery(state) is False


def test_recovery_resolved_allows_completion():
    state = RecoveryLifecycleState(step_id="s1")
    state.enter_recovery(FailureType.ELEMENT_NOT_FOUND)
    state.mark_resolved()
    assert can_complete_after_recovery(state) is True


def test_recovery_state_transitions():
    state = RecoveryLifecycleState(step_id="s1")
    assert state.status == RecoveryStatus.ACTIVE
    state.enter_recovery(FailureType.TIMEOUT)
    assert state.status == RecoveryStatus.IN_RECOVERY
    state.mark_resolved()
    assert state.status == RecoveryStatus.RESOLVED


def test_recovery_failed_closed_stays_blocked():
    state = RecoveryLifecycleState(step_id="s1")
    state.enter_recovery(FailureType.UNKNOWN)
    state.mark_failed_closed()
    assert can_complete_after_recovery(state) is False
    assert state.status == RecoveryStatus.FAILED_CLOSED


# ---------------------------------------------------------------------------
# S6-0806/0807: Resume / User Guidance
# ---------------------------------------------------------------------------

def test_failed_closed_recovery_asks_user():
    packet = RecoveryPacket(
        step_id="s1",
        failure_type=FailureType.UNKNOWN,
        error_message="Something weird happened",
        failed_locator=None,
        page_url="https://example.com",
    )
    proposal = propose_deterministic_recovery(packet)
    # Unknown failures should lead to ask_user
    assert proposal.strategy in ("ask_user", "fail_closed")
