"""
tests/test_plan_revision.py

Tests for Cluster 5: Plan Discussion / Correction / Direct Editing.
S6-0501 through S6-0506.
"""
from __future__ import annotations

import pytest
from runtime.plan_revision import (
    PlanRevisionState,
    RevisionStatus,
    PlanDiff,
    PlanDiffType,
    apply_plan_diff,
    validate_plan_diff,
    discussion_state_is_not_mutation,
)
from runtime.journey_plan import DraftPlan, JourneyStep, PlanStatus, ChildOperation


def _make_step(step_id: str, desc: str = "Step") -> JourneyStep:
    return JourneyStep(
        step_id=step_id,
        description=desc,
        page_required="login",
        preconditions=[], postconditions=[],
        expected_outcome="done",
        required_test_data=[], risk_metadata={"risk_level": "low"},
        capability_gaps=[], operations=[],
    )


def _make_plan(steps=None) -> DraftPlan:
    steps = steps or [_make_step("s1"), _make_step("s2")]
    return DraftPlan(
        plan_id="plan-1", title="Test Plan",
        steps=steps, status=PlanStatus.DRAFT,
        required_pages=["login"], dependencies=[], capability_gaps=[],
    )


# ---------------------------------------------------------------------------
# S6-0501: Discussion is not mutation
# ---------------------------------------------------------------------------

def test_discussion_does_not_mutate_plan():
    plan = _make_plan()
    original_steps = [s.step_id for s in plan.steps]
    discussion_state_is_not_mutation(plan, "Can you explain step s1?")
    # Plan unchanged
    assert [s.step_id for s in plan.steps] == original_steps


def test_discussion_state_is_separate_from_plan_state():
    state = PlanRevisionState(plan_id="plan-1")
    state.add_discussion("Could you add a logout step?")
    assert state.status == RevisionStatus.DISCUSSING
    assert state.plan_mutations == []


# ---------------------------------------------------------------------------
# S6-0502: Explicit apply/update mutation boundary
# ---------------------------------------------------------------------------

def test_apply_diff_mutates_plan():
    plan = _make_plan()
    diff = PlanDiff(
        diff_type=PlanDiffType.ADD_STEP,
        step_id="s3",
        payload=_make_step("s3", "New Step"),
    )
    result = apply_plan_diff(plan, diff)
    step_ids = [s.step_id for s in result.steps]
    assert "s3" in step_ids


def test_remove_step_diff_removes_step():
    plan = _make_plan()
    diff = PlanDiff(
        diff_type=PlanDiffType.REMOVE_STEP,
        step_id="s2",
        payload=None,
    )
    result = apply_plan_diff(plan, diff)
    step_ids = [s.step_id for s in result.steps]
    assert "s2" not in step_ids
    assert "s1" in step_ids


def test_update_step_diff_updates_description():
    plan = _make_plan()
    updated_step = _make_step("s1", "Updated Description")
    diff = PlanDiff(
        diff_type=PlanDiffType.UPDATE_STEP,
        step_id="s1",
        payload=updated_step,
    )
    result = apply_plan_diff(plan, diff)
    s1 = next(s for s in result.steps if s.step_id == "s1")
    assert s1.description == "Updated Description"


# ---------------------------------------------------------------------------
# S6-0503: Plan diff proposal schema and validator
# ---------------------------------------------------------------------------

def test_valid_diff_passes_validation():
    diff = PlanDiff(
        diff_type=PlanDiffType.ADD_STEP,
        step_id="s3",
        payload=_make_step("s3"),
    )
    errors = validate_plan_diff(diff)
    assert errors == []


def test_invalid_diff_missing_step_id_fails():
    diff = PlanDiff(
        diff_type=PlanDiffType.ADD_STEP,
        step_id="",
        payload=_make_step(""),
    )
    errors = validate_plan_diff(diff)
    assert len(errors) > 0


def test_remove_diff_with_unknown_step_fails():
    plan = _make_plan()
    diff = PlanDiff(
        diff_type=PlanDiffType.REMOVE_STEP,
        step_id="s99",  # doesn't exist
        payload=None,
    )
    # validate_plan_diff can pass (step existence checked in apply)
    # apply should handle gracefully
    result = apply_plan_diff(plan, diff)
    # s99 not in plan, so no-op or error logged — plan unchanged
    step_ids = [s.step_id for s in result.steps]
    assert "s99" not in step_ids


# ---------------------------------------------------------------------------
# S6-0504: Corrected plan_ready lifecycle
# ---------------------------------------------------------------------------

def test_corrected_plan_requires_fresh_confirmation():
    state = PlanRevisionState(plan_id="plan-1")
    state.status = RevisionStatus.PLAN_READY
    # After correction, must go back to DRAFT (needs re-confirmation)
    state.apply_correction()
    assert state.status == RevisionStatus.DRAFT


def test_plan_not_ready_while_in_discussion():
    state = PlanRevisionState(plan_id="plan-1")
    state.add_discussion("change step 1")
    assert state.status != RevisionStatus.PLAN_READY


# ---------------------------------------------------------------------------
# S6-0505: Direct plan editing backend contract
# ---------------------------------------------------------------------------

def test_direct_edit_goes_through_diff_path():
    plan = _make_plan()
    diff = PlanDiff(
        diff_type=PlanDiffType.UPDATE_STEP,
        step_id="s1",
        payload=_make_step("s1", "Directly edited step"),
    )
    errors = validate_plan_diff(diff)
    assert errors == []
    result = apply_plan_diff(plan, diff)
    s1 = next(s for s in result.steps if s.step_id == "s1")
    assert s1.description == "Directly edited step"


def test_no_silent_child_drop_on_update():
    """Updating a step should not silently drop sibling steps."""
    plan = _make_plan([_make_step("s1"), _make_step("s2"), _make_step("s3")])
    diff = PlanDiff(
        diff_type=PlanDiffType.UPDATE_STEP,
        step_id="s2",
        payload=_make_step("s2", "Updated"),
    )
    result = apply_plan_diff(plan, diff)
    step_ids = [s.step_id for s in result.steps]
    assert "s1" in step_ids
    assert "s3" in step_ids
