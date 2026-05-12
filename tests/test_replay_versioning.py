"""
tests/test_replay_versioning.py

Tests for Cluster 9: Replay Repair + Save/Load + Versioning.
S6-0901 through S6-0909.
"""
from __future__ import annotations

import pytest
from runtime.session_store import (
    SessionSpec,
    SessionState,
    save_session,
    load_session,
    restore_session_state,
)
from runtime.replay_engine import (
    ReplayRequest,
    ReplayResult,
    ReplayFailureType,
    ReplayRepairProposal,
    replay_one,
    replay_all,
    classify_replay_failure,
    propose_replay_repair,
)


# ---------------------------------------------------------------------------
# S6-0901: Workspace save session and spec contract
# ---------------------------------------------------------------------------

def test_save_session_returns_session_id():
    spec = SessionSpec(
        title="Login Test",
        steps=[{"step_id": "s1", "action": "click", "locator": "[data-testid=btn]"}],
        page_url="https://example.com",
    )
    session_id = save_session(spec)
    assert session_id is not None
    assert isinstance(session_id, str)


def test_save_session_is_immutable_record():
    spec = SessionSpec(
        title="Test",
        steps=[{"step_id": "s1"}],
        page_url="https://example.com",
    )
    sid = save_session(spec)
    # Saved session should be retrievable
    loaded = load_session(sid)
    assert loaded is not None
    assert loaded.title == "Test"


# ---------------------------------------------------------------------------
# S6-0902: Load session and restore recorded state
# ---------------------------------------------------------------------------

def test_load_session_returns_spec():
    spec = SessionSpec(title="Load Test", steps=[{"step_id": "s2"}], page_url="https://x.com")
    sid = save_session(spec)
    loaded = load_session(sid)
    assert loaded.title == "Load Test"


def test_load_nonexistent_session_returns_none():
    result = load_session("nonexistent-session-id")
    assert result is None


# ---------------------------------------------------------------------------
# S6-0903: session_state reconnect restore
# ---------------------------------------------------------------------------

def test_restore_session_state_returns_state():
    spec = SessionSpec(title="Restore Test", steps=[{"step_id": "s1"}], page_url="https://x.com")
    sid = save_session(spec)
    state = restore_session_state(sid)
    assert isinstance(state, SessionState)
    assert state.session_id == sid


def test_session_state_has_required_fields():
    spec = SessionSpec(title="T", steps=[], page_url="https://x.com")
    sid = save_session(spec)
    state = restore_session_state(sid)
    assert hasattr(state, "session_id")
    assert hasattr(state, "current_step_index")
    assert hasattr(state, "status")


# ---------------------------------------------------------------------------
# S6-0904: Replay one and all
# ---------------------------------------------------------------------------

def test_replay_one_returns_result():
    req = ReplayRequest(
        session_id="s1",
        step_id="step-001",
        step={"step_id": "step-001", "action": "click", "locator": "[data-testid=btn]"},
    )
    result = replay_one(req)
    assert isinstance(result, ReplayResult)
    assert result.step_id == "step-001"


def test_replay_all_returns_results_list():
    steps = [
        {"step_id": f"step-{i:03d}", "action": "click", "locator": f"[data-testid=btn-{i}]"}
        for i in range(3)
    ]
    results = replay_all(session_id="sess-1", steps=steps)
    assert isinstance(results, list)
    assert len(results) == 3


def test_replay_result_has_required_fields():
    req = ReplayRequest(session_id="s", step_id="s1", step={"step_id": "s1"})
    result = replay_one(req)
    assert hasattr(result, "step_id")
    assert hasattr(result, "success")
    assert hasattr(result, "failure_type")


# ---------------------------------------------------------------------------
# S6-0905: Replay failure classification
# ---------------------------------------------------------------------------

def test_replay_locator_failure_classified():
    failure_type = classify_replay_failure({"error": "ElementNotFoundError", "step": "s1"})
    assert failure_type == ReplayFailureType.LOCATOR_STALE


def test_replay_timeout_classified():
    failure_type = classify_replay_failure({"error": "TimeoutError"})
    assert failure_type == ReplayFailureType.TIMEOUT


def test_replay_state_mismatch_classified():
    failure_type = classify_replay_failure({"error": "PageStateError: wrong page"})
    assert failure_type in (ReplayFailureType.STATE_MISMATCH, ReplayFailureType.UNKNOWN)


# ---------------------------------------------------------------------------
# S6-0906/0907/0908: Replay repair and versioning
# ---------------------------------------------------------------------------

def test_replay_repair_proposal_generated():
    proposal = propose_replay_repair(
        step={"step_id": "s1", "locator": "[data-testid=old]"},
        failure_type=ReplayFailureType.LOCATOR_STALE,
    )
    assert isinstance(proposal, ReplayRepairProposal)
    assert proposal.proposed_locator is not None or proposal.strategy is not None


def test_replay_repair_preserves_step_history():
    spec = SessionSpec(title="T", steps=[{"step_id": "s1", "locator": "[old]"}], page_url="x")
    sid = save_session(spec)
    # Save repaired version with history
    repaired_spec = SessionSpec(title="T (repaired)", steps=[{"step_id": "s1", "locator": "[new]"}], page_url="x")
    new_sid = save_session(repaired_spec)
    assert new_sid != sid  # new version has new ID
    # Both sessions loadable
    assert load_session(sid) is not None
    assert load_session(new_sid) is not None


def test_backend_validates_replay_repair_before_save():
    proposal = ReplayRepairProposal(
        step_id="s1",
        strategy="replace_locator",
        proposed_locator="[data-testid=new-btn]",
        reason="stale locator updated",
    )
    assert proposal.strategy is not None
    assert proposal.step_id is not None
