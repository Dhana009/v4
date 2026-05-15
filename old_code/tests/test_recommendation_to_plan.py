"""
tests/test_recommendation_to_plan.py

Tests for S6-0306: Accepted recommendations become executable plan.
"""
from __future__ import annotations

import pytest
from runtime.recommendation_contracts import (
    PageValidationRecommenderOutput,
    ValidationRecommendation,
    ValidationRecommendationGroup,
)
from runtime.recommendation_to_plan import (
    PlanGenerationResult,
    generate_plan_from_accepted_recommendations,
)


def _make_rec(rec_id: str, section_id: str = "main", priority: str = "useful",
              rec_type: str = "assertion", capability_status: str = "supported") -> ValidationRecommendation:
    return ValidationRecommendation(
        id=rec_id,
        recommendation_type=rec_type,
        assertion_type="text_content",
        action_type=None,
        section_id=section_id,
        description=f"Check {rec_id}",
        locator_hint=f"[data-testid={rec_id}]",
        expected_value="expected",
        priority=priority,
        confidence=0.9,
        capability_status=capability_status,
    )


def _make_group(section_id: str, recs: list) -> ValidationRecommendationGroup:
    return ValidationRecommendationGroup(
        section_id=section_id,
        section_name=section_id.replace("_", " ").title(),
        recommendations=recs,
        ambiguities=[],
    )


def _make_output(recs: list) -> PageValidationRecommenderOutput:
    group = _make_group("main", recs)
    return PageValidationRecommenderOutput(
        groups=[group],
        total_recommendations=len(recs),
        critical_count=0,
        capability_gaps=[],
        warnings=[],
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_accepted_recommendations_produce_plan_children():
    recs = [_make_rec("r1"), _make_rec("r2")]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=["r1", "r2"],
        recommender_output=output,
    )
    assert isinstance(result, PlanGenerationResult)
    assert len(result.plan_operations) == 2


def test_removed_recommendations_are_excluded():
    recs = [_make_rec("r1"), _make_rec("r2"), _make_rec("r3")]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=["r1"],  # only r1 accepted
        recommender_output=output,
    )
    op_ids = [op["recommendation_id"] for op in result.plan_operations]
    assert "r1" in op_ids
    assert "r2" not in op_ids
    assert "r3" not in op_ids


def test_reordered_recommendations_preserve_order():
    recs = [_make_rec("r1"), _make_rec("r2"), _make_rec("r3")]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=["r3", "r1"],  # r3 first
        recommender_output=output,
    )
    op_ids = [op["recommendation_id"] for op in result.plan_operations]
    assert op_ids.index("r3") < op_ids.index("r1")


def test_unsupported_recommendations_marked_as_capability_gap():
    recs = [
        _make_rec("r1", capability_status="supported"),
        _make_rec("r2", capability_status="capability_gap"),
    ]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=["r1", "r2"],
        recommender_output=output,
    )
    gap_ops = [op for op in result.plan_operations if op.get("capability_status") == "capability_gap"]
    assert len(gap_ops) >= 1


def test_plan_is_validated_before_plan_ready():
    recs = [_make_rec("r1")]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=["r1"],
        recommender_output=output,
    )
    assert result.validated is True


def test_empty_accepted_ids_produces_empty_plan():
    recs = [_make_rec("r1"), _make_rec("r2")]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=[],
        recommender_output=output,
    )
    assert len(result.plan_operations) == 0


def test_plan_operations_have_required_fields():
    recs = [_make_rec("r1")]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=["r1"],
        recommender_output=output,
    )
    for op in result.plan_operations:
        assert "operation_id" in op
        assert "recommendation_id" in op
        assert "expected_outcome" in op


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_plan_ready_includes_accepted_recommendation_lineage():
    recs = [_make_rec("r1")]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=["r1"],
        recommender_output=output,
    )
    assert result.plan_operations[0]["recommendation_id"] == "r1"


def test_plan_result_is_typed():
    recs = [_make_rec("r1")]
    output = _make_output(recs)
    result = generate_plan_from_accepted_recommendations(
        request_id="req-1",
        accepted_ids=["r1"],
        recommender_output=output,
    )
    assert isinstance(result, PlanGenerationResult)
    assert hasattr(result, "plan_operations")
    assert hasattr(result, "validated")
    assert hasattr(result, "request_id")
