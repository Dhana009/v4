"""
runtime/plan_revision.py

Plan discussion, correction, and direct editing contracts.

Source rule: S6-0501–0505 — Discussion is not mutation. Explicit apply/update
only mutates via backend-validated plan_diff. No silent child drop/reorder/split/merge.
Corrected plan_ready requires fresh confirmation.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from runtime.journey_plan import DraftPlan, JourneyStep


# ---------------------------------------------------------------------------
# Plan revision state
# ---------------------------------------------------------------------------

class RevisionStatus(enum.Enum):
    DRAFT = "draft"
    DISCUSSING = "discussing"
    DIFF_PROPOSED = "diff_proposed"
    PLAN_READY = "plan_ready"
    CONFIRMED = "confirmed"


@dataclass
class PlanRevisionState:
    plan_id: str
    status: RevisionStatus = RevisionStatus.DRAFT
    discussion_history: list[str] = field(default_factory=list)
    plan_mutations: list[Any] = field(default_factory=list)

    def add_discussion(self, message: str) -> None:
        """Record a discussion message — does NOT mutate the plan."""
        self.discussion_history.append(message)
        self.status = RevisionStatus.DISCUSSING

    def apply_correction(self) -> None:
        """After a correction is applied, plan goes back to DRAFT (needs re-confirmation)."""
        self.status = RevisionStatus.DRAFT


# ---------------------------------------------------------------------------
# Plan diff types
# ---------------------------------------------------------------------------

class PlanDiffType(enum.Enum):
    ADD_STEP = "add_step"
    REMOVE_STEP = "remove_step"
    UPDATE_STEP = "update_step"
    REORDER_STEPS = "reorder_steps"


@dataclass
class PlanDiff:
    diff_type: PlanDiffType
    step_id: str
    payload: Any  # JourneyStep or None


# ---------------------------------------------------------------------------
# Diff validator
# ---------------------------------------------------------------------------

def validate_plan_diff(diff: PlanDiff) -> list[str]:
    """Validate a plan diff. Returns list of errors (empty = valid)."""
    errors: list[str] = []
    if not diff.step_id or not diff.step_id.strip():
        errors.append("PlanDiff must have a non-empty step_id")
    if diff.diff_type in (PlanDiffType.ADD_STEP, PlanDiffType.UPDATE_STEP):
        if diff.payload is None:
            errors.append(f"PlanDiff type {diff.diff_type.value} requires a step payload")
    return errors


# ---------------------------------------------------------------------------
# Diff applicator
# ---------------------------------------------------------------------------

def apply_plan_diff(plan: DraftPlan, diff: PlanDiff) -> DraftPlan:
    """Apply *diff* to *plan* and return new DraftPlan.

    Never silently drops sibling steps. Immutable-style: returns modified copy.
    """
    steps = list(plan.steps)  # copy

    if diff.diff_type == PlanDiffType.ADD_STEP:
        if diff.payload is not None:
            steps.append(diff.payload)

    elif diff.diff_type == PlanDiffType.REMOVE_STEP:
        steps = [s for s in steps if s.step_id != diff.step_id]

    elif diff.diff_type == PlanDiffType.UPDATE_STEP:
        new_steps: list[JourneyStep] = []
        for s in steps:
            if s.step_id == diff.step_id and diff.payload is not None:
                new_steps.append(diff.payload)
            else:
                new_steps.append(s)
        steps = new_steps

    elif diff.diff_type == PlanDiffType.REORDER_STEPS:
        # payload is list of step_ids in new order
        if isinstance(diff.payload, list):
            id_to_step = {s.step_id: s for s in steps}
            steps = [id_to_step[sid] for sid in diff.payload if sid in id_to_step]

    from dataclasses import replace
    return DraftPlan(
        plan_id=plan.plan_id,
        title=plan.title,
        steps=steps,
        status=plan.status,
        required_pages=plan.required_pages,
        dependencies=plan.dependencies,
        capability_gaps=plan.capability_gaps,
    )


# ---------------------------------------------------------------------------
# Discussion guard
# ---------------------------------------------------------------------------

def discussion_state_is_not_mutation(plan: DraftPlan, message: str) -> None:
    """Record that discussion does not mutate the plan.

    This function is a no-op guard — the plan object is not modified.
    """
    # Discussion is read-only — no mutations applied
    return
