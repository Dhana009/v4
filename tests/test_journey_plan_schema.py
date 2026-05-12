"""
tests/test_journey_plan_schema.py

Tests for S6-0402 + S6-0403–0408: Journey plan schema, Steps Mode, multi-step flows.
"""
from __future__ import annotations

import pytest
from runtime.journey_plan import (
    DraftPlan,
    JourneyStep,
    ChildOperation,
    PlanStatus,
    build_draft_plan,
    validate_draft_plan,
)


def _make_step(step_id: str, page: str = "login") -> JourneyStep:
    return JourneyStep(
        step_id=step_id,
        description=f"Step {step_id}",
        page_required=page,
        preconditions=[],
        postconditions=[],
        expected_outcome=f"outcome_{step_id}",
        required_test_data=[],
        risk_metadata={"risk_level": "low"},
        capability_gaps=[],
        operations=[],
    )


def _make_plan(steps: list[JourneyStep]) -> DraftPlan:
    return DraftPlan(
        plan_id="plan-1",
        title="Test Journey",
        steps=steps,
        status=PlanStatus.DRAFT,
        required_pages=["login"],
        dependencies=[],
        capability_gaps=[],
    )


# ---------------------------------------------------------------------------
# S6-0402: Draft plan schema
# ---------------------------------------------------------------------------

def test_draft_plan_has_stable_step_ids():
    steps = [_make_step("s1"), _make_step("s2")]
    plan = _make_plan(steps)
    ids = [s.step_id for s in plan.steps]
    assert ids == ["s1", "s2"]


def test_each_browser_changing_step_has_risk_metadata():
    step = _make_step("s1")
    assert step.risk_metadata is not None
    assert "risk_level" in step.risk_metadata


def test_required_data_is_explicit():
    step = JourneyStep(
        step_id="s1",
        description="Fill checkout",
        page_required="checkout",
        preconditions=[],
        postconditions=[],
        expected_outcome="form_submitted",
        required_test_data=["credit_card", "billing_address"],
        risk_metadata={"risk_level": "medium"},
        capability_gaps=[],
        operations=[],
    )
    assert "credit_card" in step.required_test_data


def test_unsupported_capability_becomes_gap():
    step = JourneyStep(
        step_id="s1",
        description="Validate CRM API",
        page_required="crm",
        preconditions=[],
        postconditions=[],
        expected_outcome="api_validated",
        required_test_data=[],
        risk_metadata={"risk_level": "high"},
        capability_gaps=["crm_api_validation"],
        operations=[],
    )
    assert "crm_api_validation" in step.capability_gaps


def test_validate_draft_plan_passes_for_valid_plan():
    steps = [_make_step("s1"), _make_step("s2")]
    plan = _make_plan(steps)
    errors = validate_draft_plan(plan)
    assert errors == []


def test_validate_draft_plan_fails_for_missing_step_ids():
    step = JourneyStep(
        step_id="",  # empty ID
        description="Step",
        page_required="login",
        preconditions=[], postconditions=[],
        expected_outcome="done",
        required_test_data=[], risk_metadata={}, capability_gaps=[], operations=[],
    )
    plan = _make_plan([step])
    errors = validate_draft_plan(plan)
    assert len(errors) > 0


def test_build_draft_plan_from_pages():
    plan = build_draft_plan(
        title="Login Journey",
        pages=["login", "dashboard"],
        context={},
    )
    assert isinstance(plan, DraftPlan)
    assert plan.status == PlanStatus.DRAFT
    assert len(plan.steps) >= 1


# ---------------------------------------------------------------------------
# S6-0403: Steps Mode intake
# ---------------------------------------------------------------------------

def test_steps_mode_requires_step_ids():
    from runtime.steps_mode import StepsModeIntake, validate_steps_mode_intake
    intake = StepsModeIntake(step_ids=[], page_state={"url": "x"})
    errors = validate_steps_mode_intake(intake)
    assert len(errors) > 0


def test_steps_mode_passes_with_valid_data():
    from runtime.steps_mode import StepsModeIntake, validate_steps_mode_intake
    intake = StepsModeIntake(step_ids=["s1", "s2"], page_state={"url": "https://example.com"})
    errors = validate_steps_mode_intake(intake)
    assert errors == []


# ---------------------------------------------------------------------------
# S6-0404: Queued multi-step planning
# ---------------------------------------------------------------------------

def test_multi_step_queue_is_ordered():
    from runtime.multi_step_queue import MultiStepQueue
    q = MultiStepQueue()
    q.enqueue("s1")
    q.enqueue("s2")
    q.enqueue("s3")
    assert q.peek() == "s1"
    assert q.dequeue() == "s1"
    assert q.peek() == "s2"


def test_multi_step_queue_not_empty():
    from runtime.multi_step_queue import MultiStepQueue
    q = MultiStepQueue()
    assert q.is_empty() is True
    q.enqueue("s1")
    assert q.is_empty() is False


# ---------------------------------------------------------------------------
# S6-0405: Selected section multi-action planning
# ---------------------------------------------------------------------------

def test_selected_section_plan_is_scoped():
    from runtime.section_action_planner import plan_actions_for_section
    result = plan_actions_for_section(
        section_id="login_form",
        elements=[
            {"role": "textbox", "label": "Username"},
            {"role": "button", "label": "Login"},
        ],
    )
    assert result.section_id == "login_form"
    assert len(result.proposed_actions) >= 1


# ---------------------------------------------------------------------------
# S6-0406: Page-state dependency model
# ---------------------------------------------------------------------------

def test_page_state_dependency_tracks_required_page():
    from runtime.page_state_model import PageStateDependency
    dep = PageStateDependency(
        step_id="s2",
        required_page="dashboard",
        current_page="login",
        satisfied=False,
    )
    assert dep.satisfied is False
    assert dep.required_page == "dashboard"


def test_page_state_dependency_satisfied_when_page_matches():
    from runtime.page_state_model import PageStateDependency
    dep = PageStateDependency(
        step_id="s2",
        required_page="dashboard",
        current_page="dashboard",
        satisfied=True,
    )
    assert dep.satisfied is True


# ---------------------------------------------------------------------------
# S6-0407: Wrong-current-page precondition flow
# ---------------------------------------------------------------------------

def test_wrong_page_precondition_blocks_step():
    from runtime.page_state_model import check_page_precondition
    result = check_page_precondition(
        step=_make_step("s1", page="dashboard"),
        current_page="login",
    )
    assert result.blocked is True
    assert result.reason is not None


def test_correct_page_allows_step():
    from runtime.page_state_model import check_page_precondition
    result = check_page_precondition(
        step=_make_step("s1", page="login"),
        current_page="login",
    )
    assert result.blocked is False
