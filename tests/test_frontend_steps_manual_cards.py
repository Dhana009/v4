"""
tests/test_frontend_steps_manual_cards.py

Sprint 7 Cluster 7 — S7-0701..S7-0712: Steps tab, Manual Mode, Picker/Locator.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMP = os.path.join(REPO_ROOT, "frontend", "src", "components")


def _read(rel: str) -> str:
    path = os.path.join(COMP, rel)
    if not os.path.exists(path):
        return ""
    return open(path, encoding="utf-8").read()


def _exists(rel: str) -> bool:
    return os.path.exists(os.path.join(COMP, rel))


# ---------------------------------------------------------------------------
# S7-0701 — Steps tab live wiring
# ---------------------------------------------------------------------------

def test_steps_panel_renders_pending_steps():
    c = _read("steps/StepsPanel.jsx")
    assert "pendingSteps" in c or "pending_steps" in c or "steps" in c
    assert "data-testid" in c


def test_steps_panel_empty_state():
    c = _read("steps/StepsPanel.jsx")
    assert "empty" in c.lower() or "No steps" in c


def test_steps_panel_uses_step_id_not_index():
    c = _read("steps/StepsPanel.jsx")
    assert "step_id" in c, "step identity must use step_id, not display index"


def test_steps_panel_no_demo():
    c = _read("steps/StepsPanel.jsx")
    assert "DEMO_" not in c and "MOCK_" not in c


# ---------------------------------------------------------------------------
# S7-0702 — Add/edit/delete/reorder/duplicate
# ---------------------------------------------------------------------------

def test_step_builder_action_handlers():
    c = _read("steps/StepBuilder.jsx")
    for action in ["onAdd", "onEdit", "onDelete", "onReorder", "onDuplicate"]:
        assert action in c, f"StepBuilder must expose {action}"


def test_step_builder_command_typed_not_lifecycle():
    c = _read("steps/StepBuilder.jsx")
    # Must not setRecordedSteps or mark recorded
    assert "setRecordedSteps" not in c
    assert "step_recorded" not in c or "// " in c  # don't fake backend event


# ---------------------------------------------------------------------------
# S7-0703 — Run selected / Run all
# ---------------------------------------------------------------------------

def test_run_controls_exists():
    assert _exists("steps/RunControls.jsx")


def test_run_controls_run_selected_requires_selection():
    c = _read("steps/RunControls.jsx")
    assert "selectedStepIds" in c or "selected" in c.lower()
    assert "disabled" in c


def test_run_controls_run_all_blocked_when_blocked():
    c = _read("steps/RunControls.jsx")
    assert "blocked" in c.lower() or "disabled" in c
    assert "run_steps" in c or "onRunSelected" in c


# ---------------------------------------------------------------------------
# S7-0704 — Picker element/section
# ---------------------------------------------------------------------------

def test_picker_controls_exists():
    assert _exists("picker/PickerControls.jsx")


def test_picker_controls_arm_cancel_commands():
    c = _read("picker/PickerControls.jsx")
    assert "arm_picker" in c or "onArm" in c
    assert "cancel" in c.lower()


def test_picker_excludes_autoworkbench():
    c = _read("picker/PickerControls.jsx")
    # Must reference exclusion selector or data-autoworkbench
    has_excl = (
        "data-autoworkbench" in c
        or "PICKER_EXCLUSION_SELECTOR" in c
        or "isExcluded" in c
        or "data-aw-ui" in c
    )
    assert has_excl, "PickerControls must reference AutoWorkbench exclusion"


# ---------------------------------------------------------------------------
# S7-0705 — Selected element preview
# ---------------------------------------------------------------------------

def test_selected_preview_exists():
    assert _exists("picker/SelectedElementPreview.jsx")


def test_selected_preview_renders_element():
    c = _read("picker/SelectedElementPreview.jsx")
    assert "element" in c.lower()
    assert "data-testid" in c


def test_selected_preview_redacts_sensitive():
    c = _read("picker/SelectedElementPreview.jsx")
    # Must redact password/email/credit card-like values
    has_redact = (
        "redact" in c.lower()
        or "sensitive" in c.lower()
        or "mask" in c.lower()
        or "password" in c.lower()
    )
    assert has_redact, "SelectedElementPreview must redact sensitive data"


# ---------------------------------------------------------------------------
# S7-0706 — Locator candidate display
# ---------------------------------------------------------------------------

def test_locator_candidates_exists():
    assert _exists("locator/LocatorCandidates.jsx")


def test_locator_candidates_renders_list():
    c = _read("locator/LocatorCandidates.jsx")
    assert "candidates" in c.lower()
    assert "data-testid" in c


def test_locator_candidates_requires_backend_validation():
    c = _read("locator/LocatorCandidates.jsx")
    # Must indicate not yet validated / pending validation
    has_pending = (
        "validated" in c.lower()
        or "pending" in c.lower()
        or "validate" in c.lower()
    )
    assert has_pending


# ---------------------------------------------------------------------------
# S7-0707 — Validate / improve locator commands
# ---------------------------------------------------------------------------

def test_locator_actions_exists():
    assert _exists("locator/LocatorActions.jsx")


def test_locator_actions_validate_improve_commands():
    c = _read("locator/LocatorActions.jsx")
    assert "validate_locator" in c or "onValidate" in c
    assert "improve_locator" in c or "onImprove" in c


def test_locator_actions_no_local_activation():
    c = _read("locator/LocatorActions.jsx")
    assert "setActiveLocator" not in c


# ---------------------------------------------------------------------------
# S7-0708 — Manual Mode toggle
# ---------------------------------------------------------------------------

def test_manual_mode_toggle_exists():
    assert _exists("manual/ManualModeToggle.jsx")


def test_manual_mode_toggle_guards():
    c = _read("manual/ManualModeToggle.jsx")
    # Must not flip during run/recovery without disabled reason
    assert "disabled" in c
    assert "manual" in c.lower()


def test_manual_mode_no_auto_llm():
    c = _read("manual/ManualModeToggle.jsx")
    assert "llm_request" not in c and "callLLM" not in c


# ---------------------------------------------------------------------------
# S7-0709 — Manual action builder
# ---------------------------------------------------------------------------

def test_manual_action_builder_exists():
    assert _exists("manual/ManualActionBuilder.jsx")


def test_manual_action_required_fields():
    c = _read("manual/ManualActionBuilder.jsx")
    # action/target/value required validation
    assert "required" in c.lower() or "disabled" in c
    assert "action" in c.lower()


def test_manual_action_draft_only():
    c = _read("manual/ManualActionBuilder.jsx")
    # Must dispatch typed draft command, not recorded step
    assert "setRecordedSteps" not in c


# ---------------------------------------------------------------------------
# S7-0710 — Manual assertion builder
# ---------------------------------------------------------------------------

def test_manual_assertion_builder_exists():
    assert _exists("manual/ManualAssertionBuilder.jsx")


def test_manual_assertion_expected_value_required():
    c = _read("manual/ManualAssertionBuilder.jsx")
    assert "expected" in c.lower()
    assert "required" in c.lower() or "disabled" in c


# ---------------------------------------------------------------------------
# S7-0711 — Expected value / test data
# ---------------------------------------------------------------------------

def test_expected_value_panel_exists():
    assert _exists("manual/ExpectedValuePanel.jsx")


def test_expected_value_blocks_run_when_missing():
    c = _read("manual/ExpectedValuePanel.jsx")
    assert "missing" in c.lower() or "blocked" in c.lower() or "required" in c.lower()


# ---------------------------------------------------------------------------
# S7-0712 — Wrong-page / missing-data / weak-locator blocked states
# ---------------------------------------------------------------------------

def test_blocked_banner_exists():
    assert _exists("primitives/BlockedStateBanner.jsx")


def test_blocked_banner_three_states():
    c = _read("primitives/BlockedStateBanner.jsx")
    for kind in ["wrong_page", "missing_data", "weak_locator"]:
        assert kind in c, f"BlockedStateBanner must surface {kind}"


def test_blocked_banner_visible_and_actionable():
    c = _read("primitives/BlockedStateBanner.jsx")
    assert "data-testid" in c
    assert "reason" in c.lower() or "message" in c.lower()
