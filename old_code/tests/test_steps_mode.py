"""
tests/test_steps_mode.py

Dedicated behavioral tests for runtime/steps_mode.py.

Source rules: S6-0403 — step IDs must be available, page state snapshot required.
No execution before confirmation.
"""
from __future__ import annotations

import pytest

from runtime.steps_mode import StepsModeIntake, validate_steps_mode_intake


# ---------------------------------------------------------------------------
# 1. Valid intake passes validation
# ---------------------------------------------------------------------------

def test_valid_intake_no_errors():
    intake = StepsModeIntake(
        step_ids=["step-001", "step-002"],
        page_state={"url": "https://example.com", "title": "Home"},
    )
    errors = validate_steps_mode_intake(intake)
    assert errors == []


def test_valid_intake_with_selected_section():
    intake = StepsModeIntake(
        step_ids=["step-100"],
        page_state={"url": "https://app.example.com/login", "dom_hash": "abc123"},
        selected_section="login-form",
    )
    errors = validate_steps_mode_intake(intake)
    assert errors == []


# ---------------------------------------------------------------------------
# 2. Stable step_id: IDs survive round-trip (not generated/overwritten)
# ---------------------------------------------------------------------------

def test_step_ids_preserved():
    ids = ["step-aaa", "step-bbb", "step-ccc"]
    intake = StepsModeIntake(
        step_ids=ids,
        page_state={"url": "https://example.com"},
    )
    # IDs must survive construction unmodified
    assert intake.step_ids == ids


def test_step_id_identity_not_reordered():
    ids = ["step-z", "step-a", "step-m"]
    intake = StepsModeIntake(
        step_ids=ids,
        page_state={"url": "https://example.com"},
    )
    assert intake.step_ids == ids  # order preserved, not sorted


# ---------------------------------------------------------------------------
# 3. Malformed intake: empty step_ids rejected
# ---------------------------------------------------------------------------

def test_empty_step_ids_rejected():
    intake = StepsModeIntake(
        step_ids=[],
        page_state={"url": "https://example.com"},
    )
    errors = validate_steps_mode_intake(intake)
    assert any("step_ids" in e for e in errors)


# ---------------------------------------------------------------------------
# 4. Malformed intake: missing page_state rejected
# ---------------------------------------------------------------------------

def test_empty_page_state_rejected():
    intake = StepsModeIntake(
        step_ids=["step-001"],
        page_state={},
    )
    errors = validate_steps_mode_intake(intake)
    assert any("page_state" in e for e in errors)


# ---------------------------------------------------------------------------
# 5. selected_section is optional (None is allowed)
# ---------------------------------------------------------------------------

def test_selected_section_defaults_to_none():
    intake = StepsModeIntake(
        step_ids=["step-001"],
        page_state={"url": "https://example.com"},
    )
    assert intake.selected_section is None


def test_selected_section_preserved_when_set():
    intake = StepsModeIntake(
        step_ids=["step-001"],
        page_state={"url": "https://example.com"},
        selected_section="checkout-form",
    )
    assert intake.selected_section == "checkout-form"


# ---------------------------------------------------------------------------
# 6. page_state is preserved as-is (element/section context)
# ---------------------------------------------------------------------------

def test_page_state_context_preserved():
    state = {
        "url": "https://example.com",
        "section_id": "hero",
        "viewport": {"width": 1280, "height": 800},
    }
    intake = StepsModeIntake(
        step_ids=["step-001"],
        page_state=state,
    )
    assert intake.page_state is state


# ---------------------------------------------------------------------------
# 7. No raw secrets in test data
# ---------------------------------------------------------------------------

def test_test_data_no_secrets():
    """Test data used in this file must not embed raw secrets."""
    page_states = [
        {"url": "https://example.com"},
        {"url": "https://app.example.com/login", "dom_hash": "abc123"},
        {"url": "https://example.com", "section_id": "hero"},
    ]
    for ps in page_states:
        for val in ps.values():
            assert "password" not in str(val).lower()
            assert "secret" not in str(val).lower()
            assert "sk-" not in str(val)
            assert "api_key" not in str(val).lower()


# ---------------------------------------------------------------------------
# 8. Both errors returned when both fields invalid
# ---------------------------------------------------------------------------

def test_both_fields_invalid_returns_multiple_errors():
    intake = StepsModeIntake(
        step_ids=[],
        page_state={},
    )
    errors = validate_steps_mode_intake(intake)
    assert len(errors) >= 2


# ---------------------------------------------------------------------------
# 9. Multiple step_ids all preserved
# ---------------------------------------------------------------------------

def test_multiple_step_ids_preserved():
    ids = [f"step-{i:03d}" for i in range(10)]
    intake = StepsModeIntake(
        step_ids=ids,
        page_state={"url": "https://example.com"},
    )
    assert len(intake.step_ids) == 10
    assert intake.step_ids == ids
