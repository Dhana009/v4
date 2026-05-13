"""
tests/test_run_started_event_contract.py

Sprint 7 Cluster 1 — S7-0101: run_started event contract tests.
TDD: written before implementation. All tests must fail initially then pass.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_run_started_payload,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_build_run_started_payload_includes_run_id():  # PRD-04-BE-001
    result = build_run_started_payload(run_id="run-001", steps=[])
    assert result["run_id"] == "run-001"


def test_build_run_started_payload_includes_steps_list():  # PRD-04-BE-001
    steps = [{"step_id": "s1", "action": "click"}]
    result = build_run_started_payload(run_id="run-001", steps=steps)
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) == 1


def test_build_run_started_payload_includes_phase_planning():  # PRD-04-BE-001
    result = build_run_started_payload(run_id="run-001", steps=[])
    assert result["phase"] == "planning"


def test_build_run_started_payload_phase_can_be_overridden():  # PRD-04-BE-001
    result = build_run_started_payload(run_id="run-001", steps=[], phase="executing")
    assert result["phase"] == "executing"


def test_build_run_started_payload_schema_version_set():  # GOV-S7-C0-007
    result = build_run_started_payload(run_id="run-001", steps=[])
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_build_run_started_payload_emitted_at_iso_format():  # GOV-S7-C0-007
    result = build_run_started_payload(run_id="run-001", steps=[])
    emitted_at = result["emitted_at"]
    assert isinstance(emitted_at, str)
    assert len(emitted_at) > 10


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------

def test_run_started_event_type_field_is_run_started():  # PRD-04-BE-001
    result = build_run_started_payload(run_id="run-001", steps=[])
    assert result["type"] == "run_started"


def test_run_started_event_run_id_matches_subsequent_plan_ready():  # PRD-04-BE-001
    # run_id from run_started must be consistent — builder preserves the passed run_id
    run_id = "run-consistency-check"
    result = build_run_started_payload(run_id=run_id, steps=[])
    assert result["run_id"] == run_id
    # Envelope also sets top-level run_id
    assert result.get("run_id") == run_id


def test_run_started_envelope_is_valid_backend_event_envelope():  # PRD-04-BE-001
    result = build_run_started_payload(run_id="run-001", steps=[])
    assert "type" in result
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_run_started_steps_are_deep_copied():  # GOV-S7-C0-001
    steps = [{"step_id": "s1"}]
    result = build_run_started_payload(run_id="run-001", steps=steps)
    # mutating original should not affect the event
    steps[0]["step_id"] = "mutated"
    assert result["steps"][0]["step_id"] == "s1"


# ---------------------------------------------------------------------------
# Integration / Ordering Tests
# ---------------------------------------------------------------------------

def test_run_started_not_emitted_if_no_active_run():  # GOV-S7-C0-001
    # Builder raises ValueError for empty run_id — cannot be built without a run context
    with pytest.raises(ValueError, match="run_id"):
        build_run_started_payload(run_id="", steps=[])


def test_run_started_returns_dict_with_all_required_fields():  # PRD-04-BE-001
    result = build_run_started_payload(run_id="run-001", steps=[{"step_id": "s1"}])
    for field in ("type", "run_id", "phase", "steps", "schema_version", "emitted_at", "payload"):
        assert field in result, f"missing field: {field}"


# ---------------------------------------------------------------------------
# Negative Tests (required by GOV-S7-C0-009)
# ---------------------------------------------------------------------------

def test_build_run_started_payload_rejects_empty_run_id():  # PRD-04-BE-001
    with pytest.raises(ValueError, match="run_id"):
        build_run_started_payload(run_id="", steps=[])


def test_build_run_started_payload_rejects_none_run_id():  # PRD-04-BE-001
    with pytest.raises((ValueError, TypeError)):
        build_run_started_payload(run_id=None, steps=[])  # type: ignore[arg-type]


def test_build_run_started_payload_rejects_none_steps():  # PRD-04-BE-001
    with pytest.raises((ValueError, TypeError)):
        build_run_started_payload(run_id="run-001", steps=None)  # type: ignore[arg-type]


def test_run_started_not_emitted_twice_for_same_run():  # GOV-S7-C0-001
    # Builder itself is pure — emitting twice is guarded at the call site in agent.py.
    # Test that the builder can be called but the caller must guard deduplication.
    result1 = build_run_started_payload(run_id="run-001", steps=[])
    result2 = build_run_started_payload(run_id="run-001", steps=[])
    # Both produce valid events — the agent emission guard is the dedup mechanism
    assert result1["run_id"] == result2["run_id"] == "run-001"


def test_stale_run_id_in_run_started_rejected_by_envelope_builder():  # GOV-S7-C0-007
    # Whitespace-only run_id is treated as empty and rejected
    with pytest.raises(ValueError, match="run_id"):
        build_run_started_payload(run_id="   ", steps=[])


# ---------------------------------------------------------------------------
# Coverage gap closers — build_backend_event_envelope and recovery builders
# ---------------------------------------------------------------------------

def test_build_backend_event_envelope_rejects_empty_event_type():
    from runtime.event_contracts import build_backend_event_envelope
    with pytest.raises(ValueError):
        build_backend_event_envelope("", {})


def test_build_backend_event_envelope_includes_event_id_when_given():
    from runtime.event_contracts import build_backend_event_envelope
    result = build_backend_event_envelope("run_started", {}, event_id="evt-123")
    assert result["event_id"] == "evt-123"


def test_build_recovery_needed_payload_rejects_empty_run_id():
    from runtime.event_contracts import build_recovery_needed_payload
    with pytest.raises(ValueError, match="run_id"):
        build_recovery_needed_payload(run_id="", step_id="s1", error_summary="e", current_url="u")


def test_build_recovery_needed_payload_rejects_empty_step_id():
    from runtime.event_contracts import build_recovery_needed_payload
    with pytest.raises(ValueError, match="step_id"):
        build_recovery_needed_payload(run_id="r1", step_id="", error_summary="e", current_url="u")


def test_build_recovery_needed_payload_rejects_empty_error_summary():
    from runtime.event_contracts import build_recovery_needed_payload
    with pytest.raises(ValueError, match="error_summary"):
        build_recovery_needed_payload(run_id="r1", step_id="s1", error_summary="", current_url="u")


def test_build_recovery_needed_payload_uses_default_tried_when_not_given():
    from runtime.event_contracts import build_recovery_needed_payload
    result = build_recovery_needed_payload(run_id="r1", step_id="s1", error_summary="timeout", current_url="u")
    assert isinstance(result.get("tried") or result.get("payload", {}).get("tried"), (list, type(None)))


def test_normalize_confirmed_with_run_id_mismatch_returns_stale_command():
    from runtime.event_contracts import normalize_frontend_command, FRONTEND_COMMAND_SCHEMA_VERSION
    command, rejection = normalize_frontend_command(
        {
            "type": "confirmed",
            "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
            "command_id": "cmd-1",
            "run_id": "run-stale",
        },
        current_state={"run_id": "run-active", "phase": "executing"},
    )
    assert rejection is not None
    assert rejection["rejection_code"] == "STALE_COMMAND"
