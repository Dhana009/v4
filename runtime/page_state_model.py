"""
runtime/page_state_model.py

Page-state dependency model and wrong-page precondition flow.

Source rule: S6-0406/S6-0407 — each step has required page state.
Wrong-page precondition blocks step execution. Dependency tracked explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PageStateDependency:
    step_id: str
    required_page: str
    current_page: str
    satisfied: bool


@dataclass
class PreconditionCheckResult:
    step_id: str
    blocked: bool
    reason: str | None


def check_page_precondition(step: Any, current_page: str) -> PreconditionCheckResult:
    """Check if current page satisfies the step's required page.

    Returns PreconditionCheckResult with blocked=True if wrong page.
    """
    required = getattr(step, "page_required", None)
    if required and required != current_page:
        return PreconditionCheckResult(
            step_id=step.step_id,
            blocked=True,
            reason=f"Step requires page '{required}' but current page is '{current_page}'",
        )
    return PreconditionCheckResult(
        step_id=step.step_id,
        blocked=False,
        reason=None,
    )
