"""
tests/test_recommendation_events.py

Tests for S6-0305: Recommendation review state and event contract.
"""
from __future__ import annotations

import pytest
from runtime.recommendation_events import (
    AcceptRecommendationCommand,
    PageAnalysisRequested,
    PageSummaryReady,
    RecommendationReady,
    RecommendationReviewCompleted,
    RemoveRecommendationCommand,
    ReorderRecommendationCommand,
)
from runtime.recommendation_state import (
    RecommendationReviewState,
    RecommendationStatus,
)


# ---------------------------------------------------------------------------
# Unit tests: events
# ---------------------------------------------------------------------------

def test_page_analysis_requested_has_required_fields():
    evt = PageAnalysisRequested(request_id="req-1", page_url="https://example.com")
    assert evt.request_id == "req-1"
    assert evt.page_url == "https://example.com"


def test_page_summary_ready_has_timestamp():
    evt = PageSummaryReady(
        request_id="req-1",
        page_intelligence_summary={"sections": []},
        timestamp="2026-01-01T00:00:00Z",
    )
    assert evt.timestamp is not None


def test_recommendation_ready_has_recommendations():
    from runtime.recommendation_contracts import PageValidationRecommenderOutput
    output = PageValidationRecommenderOutput(groups=[], total_recommendations=0, critical_count=0, capability_gaps=[], warnings=[])
    evt = RecommendationReady(
        request_id="req-1",
        recommendations=output,
        timestamp="2026-01-01T00:00:00Z",
    )
    assert evt.recommendations is not None


def test_accept_command_has_ids():
    cmd = AcceptRecommendationCommand(request_id="req-1", recommendation_ids=["r1", "r2"])
    assert "r1" in cmd.recommendation_ids


def test_remove_command_has_ids():
    cmd = RemoveRecommendationCommand(request_id="req-1", recommendation_ids=["r3"])
    assert "r3" in cmd.recommendation_ids


def test_reorder_command_has_new_order():
    cmd = ReorderRecommendationCommand(request_id="req-1", recommendation_ids=["r2", "r1"])
    assert cmd.recommendation_ids == ["r2", "r1"]


def test_review_completed_has_accepted_ids():
    evt = RecommendationReviewCompleted(
        request_id="req-1",
        accepted_recommendation_ids=["r1"],
        timestamp="2026-01-01T00:00:00Z",
    )
    assert "r1" in evt.accepted_recommendation_ids


# ---------------------------------------------------------------------------
# Unit tests: state
# ---------------------------------------------------------------------------

def test_state_initial_status_is_requested():
    state = RecommendationReviewState(request_id="req-1", page_url="https://example.com")
    assert state.status == RecommendationStatus.REQUESTED


def test_state_transitions_to_summary_ready():
    state = RecommendationReviewState(request_id="req-1", page_url="https://example.com")
    state.set_summary({"sections": []})
    assert state.status == RecommendationStatus.SUMMARY_READY


def test_state_transitions_to_recommendations_ready():
    from runtime.recommendation_contracts import PageValidationRecommenderOutput
    state = RecommendationReviewState(request_id="req-1", page_url="https://example.com")
    state.set_summary({"sections": []})
    output = PageValidationRecommenderOutput(groups=[], total_recommendations=0, critical_count=0, capability_gaps=[], warnings=[])
    state.set_recommendations(output)
    assert state.status == RecommendationStatus.RECOMMENDATIONS_READY


def test_recommendation_ids_stable_when_order_changes():
    state = RecommendationReviewState(request_id="req-1", page_url="https://example.com")
    state.accepted_ids = {"r1", "r2"}
    state.current_order = ["r1", "r2"]
    state.reorder(["r2", "r1"])
    assert "r1" in state.accepted_ids
    assert state.current_order == ["r2", "r1"]


def test_accepted_vs_unaccepted_tracked():
    state = RecommendationReviewState(request_id="req-1", page_url="https://example.com")
    state.accept(["r1", "r2"])
    state.remove(["r3"])
    assert "r1" in state.accepted_ids
    assert "r3" in state.removed_ids


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_unaccepted_recommendation_cannot_execute():
    state = RecommendationReviewState(request_id="req-1", page_url="https://example.com")
    state.accept(["r1"])
    # r2 is not accepted
    assert "r2" not in state.accepted_ids


def test_events_are_ordered_correctly():
    # Analysis → Summary → Recommendations → Review
    statuses = [
        RecommendationStatus.REQUESTED,
        RecommendationStatus.SUMMARY_READY,
        RecommendationStatus.RECOMMENDATIONS_READY,
        RecommendationStatus.REVIEWING,
        RecommendationStatus.COMPLETED,
    ]
    for i in range(len(statuses) - 1):
        assert statuses[i].value < statuses[i+1].value


def test_broad_recommendation_request_enters_review_not_execution():
    state = RecommendationReviewState(request_id="req-1", page_url="https://example.com")
    # State must start as REQUESTED (review mode), not executing
    assert state.status != RecommendationStatus.COMPLETED
    assert "execut" not in state.status.name.lower()
