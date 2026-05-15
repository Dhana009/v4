"""
runtime/recommendation_to_plan.py

Convert accepted recommendations into a backend-validated plan draft.

Source rule: S6-0306 — accepted recommendations → plan operations.
Removed recommendations excluded. Order preserved. No execution before
confirmation. No auto-recording, no code_update.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from runtime.recommendation_contracts import (
    PageValidationRecommenderOutput,
    ValidationRecommendation,
)


# ---------------------------------------------------------------------------
# Plan generation result
# ---------------------------------------------------------------------------

@dataclass
class PlanGenerationResult:
    request_id: str
    plan_operations: list[dict[str, Any]]
    validated: bool
    validation_errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Plan generator
# ---------------------------------------------------------------------------

def _find_recommendation(
    rec_id: str,
    recommender_output: PageValidationRecommenderOutput,
) -> ValidationRecommendation | None:
    for group in recommender_output.groups:
        for rec in group.recommendations:
            if rec.id == rec_id:
                return rec
    return None


def _generate_operation(rec: ValidationRecommendation) -> dict[str, Any]:
    """Convert a single recommendation into a plan operation."""
    return {
        "operation_id": f"op-{uuid.uuid4().hex[:8]}",
        "recommendation_id": rec.id,
        "operation_type": rec.recommendation_type,
        "assertion_type": rec.assertion_type,
        "action_type": rec.action_type,
        "section_id": rec.section_id,
        "description": rec.description,
        "locator_hint": rec.locator_hint,
        "expected_outcome": rec.expected_value or f"verify_{rec.recommendation_type}",
        "priority": rec.priority,
        "capability_status": rec.capability_status,
    }


def _validate_operations(operations: list[dict[str, Any]]) -> list[str]:
    """Validate all operations have required fields. Returns list of errors."""
    errors: list[str] = []
    for op in operations:
        for required in ("operation_id", "recommendation_id", "expected_outcome"):
            if not op.get(required):
                errors.append(f"Operation missing {required!r}: {op}")
    return errors


def generate_plan_from_accepted_recommendations(
    request_id: str,
    accepted_ids: list[str],
    recommender_output: PageValidationRecommenderOutput,
) -> PlanGenerationResult:
    """Convert accepted recommendations into a validated plan draft.

    - Only accepted_ids become operations.
    - Order follows accepted_ids list.
    - Capability gaps marked but included (user decides).
    - No execution before confirmation.
    """
    operations: list[dict[str, Any]] = []

    for rec_id in accepted_ids:
        rec = _find_recommendation(rec_id, recommender_output)
        if rec is None:
            continue
        op = _generate_operation(rec)
        operations.append(op)

    # Validate
    errors = _validate_operations(operations)
    validated = len(errors) == 0

    return PlanGenerationResult(
        request_id=request_id,
        plan_operations=operations,
        validated=validated,
        validation_errors=errors,
    )
