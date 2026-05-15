"""
runtime/journey_plan.py

Draft plan schema for journey planner.

Source rule: S6-0402 — draft plan with steps, child operations, preconditions,
postconditions, expected outcomes, required page state, dependencies,
required test data, permission/risk metadata, capability gaps.
No execution, no recording.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Any


class PlanStatus(enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    INVALID = "invalid"
    EXECUTING = "executing"
    COMPLETED = "completed"


@dataclass
class ChildOperation:
    operation_id: str
    operation_type: str    # "click" | "fill" | "assert" | etc.
    target_description: str
    locator_hint: str
    expected_outcome: str
    capability_status: str = "supported"


@dataclass
class JourneyStep:
    step_id: str
    description: str
    page_required: str
    preconditions: list[str]
    postconditions: list[str]
    expected_outcome: str
    required_test_data: list[str]
    risk_metadata: dict[str, Any]
    capability_gaps: list[str]
    operations: list[ChildOperation]


@dataclass
class DraftPlan:
    plan_id: str
    title: str
    steps: list[JourneyStep]
    status: PlanStatus
    required_pages: list[str]
    dependencies: list[str]
    capability_gaps: list[str]


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_draft_plan(
    title: str,
    pages: list[str],
    context: dict[str, Any],
) -> DraftPlan:
    """Build a minimal draft plan from *pages* list."""
    steps: list[JourneyStep] = []
    for i, page in enumerate(pages):
        step = JourneyStep(
            step_id=f"step-{i+1:03d}",
            description=f"Interact with {page} page",
            page_required=page,
            preconditions=[f"on_{page}_page"] if i > 0 else [],
            postconditions=[f"{page}_completed"],
            expected_outcome=f"{page}_validated",
            required_test_data=[],
            risk_metadata={"risk_level": "low"},
            capability_gaps=[],
            operations=[],
        )
        steps.append(step)

    return DraftPlan(
        plan_id=f"plan-{uuid.uuid4().hex[:8]}",
        title=title,
        steps=steps,
        status=PlanStatus.DRAFT,
        required_pages=pages,
        dependencies=[],
        capability_gaps=[],
    )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_draft_plan(plan: DraftPlan) -> list[str]:
    """Validate a draft plan. Returns list of error strings (empty = valid)."""
    errors: list[str] = []
    for step in plan.steps:
        if not step.step_id or not step.step_id.strip():
            errors.append(f"Step missing step_id: {step.description!r}")
        if not step.expected_outcome:
            errors.append(f"Step {step.step_id!r} missing expected_outcome")
    return errors
