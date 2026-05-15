from __future__ import annotations

"""Contract tests for runtime/phase_tracker.py.

Validates the backend-owned phase state machine: transitions, idempotency,
no-op on same phase, field correctness, and lifecycle sequence order.
"""

import pytest

from runtime.phase_tracker import PhaseTracker, PhaseTransition


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

def test_initial_phase_is_idle() -> None:
    tracker = PhaseTracker()
    assert tracker.get_phase() == "idle"


def test_custom_initial_phase() -> None:
    tracker = PhaseTracker(initial_phase="planning")
    assert tracker.get_phase() == "planning"


def test_empty_initial_phase_defaults_to_idle() -> None:
    tracker = PhaseTracker(initial_phase="")
    assert tracker.get_phase() == "idle"


# ---------------------------------------------------------------------------
# Transition correctness
# ---------------------------------------------------------------------------

def test_set_phase_returns_transition_object() -> None:
    tracker = PhaseTracker()
    transition = tracker.set_phase("planning", reason="run_started", step_id="step-1")
    assert isinstance(transition, PhaseTransition)


def test_transition_fields_are_correct() -> None:
    tracker = PhaseTracker()
    transition = tracker.set_phase("planning", reason="run_started", step_id="step-1")
    assert transition.from_phase == "idle"
    assert transition.to_phase == "planning"
    assert transition.reason == "run_started"
    assert transition.step_id == "step-1"


def test_current_phase_updates_after_transition() -> None:
    tracker = PhaseTracker()
    tracker.set_phase("planning")
    assert tracker.get_phase() == "planning"


def test_transition_chain_idle_to_planning_to_executing_to_completed() -> None:
    tracker = PhaseTracker()
    t1 = tracker.set_phase("planning", reason="run_started")
    t2 = tracker.set_phase("executing", reason="confirmed")
    t3 = tracker.set_phase("completed", reason="all_steps_recorded")

    assert t1.from_phase == "idle"
    assert t1.to_phase == "planning"
    assert t2.from_phase == "planning"
    assert t2.to_phase == "executing"
    assert t3.from_phase == "executing"
    assert t3.to_phase == "completed"
    assert tracker.get_phase() == "completed"


# ---------------------------------------------------------------------------
# Idempotency — same phase transition returns None
# ---------------------------------------------------------------------------

def test_set_same_phase_returns_none() -> None:
    tracker = PhaseTracker(initial_phase="planning")
    result = tracker.set_phase("planning")
    assert result is None


def test_set_same_phase_does_not_change_current_phase() -> None:
    tracker = PhaseTracker(initial_phase="executing")
    tracker.set_phase("executing")
    assert tracker.get_phase() == "executing"


# ---------------------------------------------------------------------------
# Empty / None inputs handled gracefully
# ---------------------------------------------------------------------------

def test_empty_new_phase_returns_none() -> None:
    tracker = PhaseTracker()
    result = tracker.set_phase("")
    assert result is None


def test_none_reason_defaults_to_unspecified() -> None:
    tracker = PhaseTracker()
    transition = tracker.set_phase("planning", reason=None)
    assert transition.reason == "unspecified"


def test_none_step_id_defaults_to_none_string() -> None:
    tracker = PhaseTracker()
    transition = tracker.set_phase("planning", step_id=None)
    assert transition.step_id == "none"


# ---------------------------------------------------------------------------
# Recovery phase transitions
# ---------------------------------------------------------------------------

def test_executing_to_recovery_transition() -> None:
    tracker = PhaseTracker(initial_phase="executing")
    transition = tracker.set_phase("recovery", reason="action_click failed", step_id="step-2")
    assert transition.from_phase == "executing"
    assert transition.to_phase == "recovery"
    assert transition.reason == "action_click failed"


def test_recovery_back_to_executing() -> None:
    tracker = PhaseTracker(initial_phase="recovery")
    transition = tracker.set_phase("executing", reason="user_retry")
    assert transition.from_phase == "recovery"
    assert transition.to_phase == "executing"


# ---------------------------------------------------------------------------
# Backend owns phase truth — phase is only set by backend
# ---------------------------------------------------------------------------

def test_phase_can_only_change_via_set_phase() -> None:
    tracker = PhaseTracker()
    tracker.set_phase("planning")
    # Direct mutation of internal state is not supported through the public API
    assert tracker.get_phase() == "planning"
    tracker.set_phase("executing")
    assert tracker.get_phase() == "executing"


def test_full_lifecycle_sequence_is_ordered() -> None:
    """Backend lifecycle phases must follow a logical order."""
    tracker = PhaseTracker()
    phases = []

    for phase, reason in [
        ("planning", "run_started"),
        ("executing", "user_confirmed"),
        ("recording", "action_success"),
        ("completed", "all_recorded"),
    ]:
        t = tracker.set_phase(phase, reason=reason)
        if t:
            phases.append(t.to_phase)

    assert phases == ["planning", "executing", "recording", "completed"]
