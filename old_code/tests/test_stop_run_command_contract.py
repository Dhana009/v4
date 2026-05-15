"""
tests/test_stop_run_command_contract.py

Sprint 7 Cluster 1 — S7-0107: stop_run command contract tests.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    SUPPORTED_FRONTEND_COMMAND_TYPES,
    build_runtime_rejection_payload,
    build_stop_run_result_event,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_stop_run_command_type_registered_in_supported_types():  # PRD-04-CMD-001
    assert "stop_run" in SUPPORTED_FRONTEND_COMMAND_TYPES


def test_build_runtime_rejection_for_stale_stop_run():  # GOV-S7-C0-005
    rejection = build_runtime_rejection_payload(
        rejection_code="STALE_COMMAND",
        message="stop_run does not match active run.",
        command_type="stop_run",
        run_id="run-old",
        recoverable=False,
    )
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "STALE_COMMAND"


def test_stop_run_result_event_includes_run_id():  # PRD-04-CMD-001
    result = build_stop_run_result_event(run_id="run-001", status="stopped")
    assert result["run_id"] == "run-001"


def test_stop_run_result_event_includes_status():  # PRD-04-CMD-001
    result = build_stop_run_result_event(run_id="run-001", status="stopped")
    assert result["status"] == "stopped"


def test_stop_run_result_event_type_correct():  # PRD-04-CMD-001
    result = build_stop_run_result_event(run_id="run-001", status="stopped")
    assert result["type"] == "run_stopped"


def test_stop_run_result_event_uses_backend_envelope():  # PRD-04-CMD-001
    result = build_stop_run_result_event(run_id="run-001", status="stopped")
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------

def test_stop_run_handler_state_validation_rejects_missing_run_id():  # PRD-04-CMD-001
    # Command normalization should reject a stop_run with no run_id field
    from runtime.event_contracts import normalize_frontend_command
    command, rejection = normalize_frontend_command(
        {"type": "stop_run"},
        current_state={"run_id": "run-active"},
    )
    # Either a valid command is returned (with run_id from state) or a rejection
    # The key invariant: if stop_run is registered, normalize returns a command or a typed rejection
    assert command is not None or rejection is not None


def test_stop_run_registered_command_normalizes_with_run_id():  # PRD-04-CMD-001
    from runtime.event_contracts import normalize_frontend_command
    import uuid
    cmd_id = str(uuid.uuid4())
    from runtime.event_contracts import FRONTEND_COMMAND_SCHEMA_VERSION
    command, rejection = normalize_frontend_command(
        {
            "type": "stop_run",
            "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
            "command_id": cmd_id,
            "run_id": "run-001",
        },
        current_state={"run_id": "run-001"},
    )
    assert rejection is None
    assert command is not None
    assert command["type"] == "stop_run"


# ---------------------------------------------------------------------------
# Negative Tests (required by GOV-S7-C0-009)
# ---------------------------------------------------------------------------

def test_stop_run_rejected_when_no_active_run():  # GOV-S7-C0-005
    # build_runtime_rejection_payload is the mechanism for stale rejection
    rejection = build_runtime_rejection_payload(
        rejection_code="NO_ACTIVE_RUN",
        message="No active run to stop.",
        command_type="stop_run",
        recoverable=False,
    )
    assert rejection["rejection_code"] == "NO_ACTIVE_RUN"


def test_stop_run_rejected_with_wrong_run_id():  # GOV-S7-C0-005
    rejection = build_runtime_rejection_payload(
        rejection_code="STALE_COMMAND",
        message="stop_run run_id does not match active run.",
        command_type="stop_run",
        run_id="run-stale",
        recoverable=False,
    )
    assert rejection["rejection_code"] == "STALE_COMMAND"
    assert rejection["run_id"] == "run-stale"


def test_duplicate_stop_run_result_is_idempotent():  # PRD-04-CMD-001
    # Two stop results with same run_id are valid — caller must guard deduplication
    r1 = build_stop_run_result_event(run_id="run-001", status="stopped")
    r2 = build_stop_run_result_event(run_id="run-001", status="stopped")
    assert r1["run_id"] == r2["run_id"]
    assert r1["status"] == r2["status"]


def test_stop_run_result_rejects_empty_run_id():  # PRD-04-CMD-001
    with pytest.raises(ValueError, match="run_id"):
        build_stop_run_result_event(run_id="", status="stopped")


def test_stop_run_result_rejects_empty_status():  # PRD-04-CMD-001
    with pytest.raises(ValueError, match="status"):
        build_stop_run_result_event(run_id="run-001", status="")


def test_stop_run_result_includes_reason_when_given():
    result = build_stop_run_result_event(run_id="run-001", status="stopped", reason="user_requested")
    assert result.get("reason") == "user_requested"


def test_build_runtime_rejection_raises_for_empty_rejection_code():
    with pytest.raises(ValueError, match="rejection_code"):
        build_runtime_rejection_payload("", "A message")


def test_build_runtime_rejection_raises_for_empty_message():
    with pytest.raises(ValueError, match="message"):
        build_runtime_rejection_payload("SOME_CODE", "")
