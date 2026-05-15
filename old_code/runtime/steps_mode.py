"""
runtime/steps_mode.py

Steps Mode backend intake: scoped step builder for LLM Mode.

Source rule: S6-0403 — step IDs must be available, page state snapshot required.
No execution before confirmation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepsModeIntake:
    step_ids: list[str]
    page_state: dict[str, Any]
    selected_section: str | None = None


def validate_steps_mode_intake(intake: StepsModeIntake) -> list[str]:
    """Validate StepsModeIntake. Returns list of errors (empty = valid)."""
    errors: list[str] = []
    if not intake.step_ids:
        errors.append("step_ids must not be empty")
    if not intake.page_state:
        errors.append("page_state must be provided")
    return errors
