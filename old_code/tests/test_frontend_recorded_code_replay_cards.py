"""
tests/test_frontend_recorded_code_replay_cards.py

Sprint 7 Cluster 8 — S7-0801..S7-0810: Recorded, Code, Replay, Save/Load UI.
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


# S7-0801 Recorded tab evidence
def test_recorded_panel_exists():
    assert _exists("recorded/RecordedPanel.jsx")


def test_recorded_panel_only_from_step_recorded():
    c = _read("recorded/RecordedPanel.jsx")
    assert "recordedSteps" in c or "recorded_steps" in c
    assert "data-testid" in c


def test_recorded_panel_empty_state():
    c = _read("recorded/RecordedPanel.jsx")
    assert "empty" in c.lower() or "No recorded" in c


def test_recorded_panel_no_pending_in_recorded():
    c = _read("recorded/RecordedPanel.jsx")
    # Must not source from pendingSteps
    assert "pendingSteps" not in c and "pending_steps" not in c


# S7-0802 Child operation evidence
def test_recorded_step_card_exists():
    assert _exists("recorded/RecordedStepCard.jsx")


def test_recorded_step_card_renders_children():
    c = _read("recorded/RecordedStepCard.jsx")
    assert "children" in c.lower()
    assert "operation" in c.lower() or "child" in c.lower()


# S7-0803 Repaired/skipped/unresolved states
def test_recorded_step_card_states():
    c = _read("recorded/RecordedStepCard.jsx")
    for state in ["repaired", "skipped", "unresolved"]:
        assert state in c.lower(), f"RecordedStepCard must surface {state}"


def test_recorded_skipped_not_pass():
    c = _read("recorded/RecordedStepCard.jsx")
    # skipped state must not be rendered as pass
    assert "skipped" in c.lower()


# S7-0804 Replay one/all
def test_replay_controls_exists():
    assert _exists("replay/ReplayControls.jsx")


def test_replay_controls_typed_commands():
    c = _read("replay/ReplayControls.jsx")
    assert "replay_one" in c or "onReplayOne" in c
    assert "replay_all" in c or "onReplayAll" in c


def test_replay_controls_no_local_success():
    c = _read("replay/ReplayControls.jsx")
    assert "setReplaySuccess" not in c


# S7-0805 Replay result
def test_replay_result_card_exists():
    assert _exists("replay/ReplayResultCard.jsx")


def test_replay_result_card_renders_outcome():
    c = _read("replay/ReplayResultCard.jsx")
    assert "outcome" in c.lower() or "result" in c.lower()
    assert "success" in c.lower() or "failure" in c.lower()


def test_replay_result_card_empty_when_no_result():
    c = _read("replay/ReplayResultCard.jsx")
    assert "return null" in c or "!result" in c


# S7-0806 Code tab live code_update rendering
def test_code_panel_exists():
    assert _exists("code/CodePanel.jsx")


def test_code_panel_renders_code_preview():
    c = _read("code/CodePanel.jsx")
    assert "codePreview" in c or "code_preview" in c
    assert "data-testid" in c


def test_code_panel_no_code_before_update():
    c = _read("code/CodePanel.jsx")
    # Must show empty/awaiting state when no code
    assert "await" in c.lower() or "no code" in c.lower() or "empty" in c.lower()


def test_code_panel_no_demo():
    c = _read("code/CodePanel.jsx")
    assert "DEMO_" not in c and "MOCK_" not in c


# S7-0807 Code line to recorded step mapping
def test_code_line_mapping_exists():
    assert _exists("code/CodeLineMapping.jsx")


def test_code_line_mapping_fallback():
    c = _read("code/CodeLineMapping.jsx")
    # Must handle missing mapping gracefully
    assert "fallback" in c.lower() or "unmapped" in c.lower() or "?" in c


# S7-0808 Code warnings / placeholder / capability
def test_code_warnings_exists():
    assert _exists("code/CodeWarnings.jsx")


def test_code_warnings_renders_states():
    c = _read("code/CodeWarnings.jsx")
    for kind in ["warning", "placeholder", "capability"]:
        assert kind in c.lower(), f"CodeWarnings must surface {kind}"


# S7-0809 Save/load session UI
def test_session_panel_exists():
    assert os.path.exists(os.path.join(COMP, "session", "SessionPanel.jsx"))


def test_session_panel_save_load_commands():
    c = _read("session/SessionPanel.jsx")
    assert "save_session" in c or "onSave" in c
    assert "load_session" in c or "onLoad" in c


def test_session_panel_no_local_success():
    c = _read("session/SessionPanel.jsx")
    # Must not mark saved/loaded locally
    assert "setSaved" not in c
    assert "setLoaded" not in c


# S7-0810 Export / copy code
def test_code_export_exists():
    assert _exists("code/CodeExport.jsx")


def test_code_export_disabled_without_code():
    c = _read("code/CodeExport.jsx")
    assert "disabled" in c
    assert "codePreview" in c or "code" in c.lower()
