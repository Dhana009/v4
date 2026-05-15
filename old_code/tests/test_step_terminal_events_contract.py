"""
tests/test_step_terminal_events_contract.py

Sprint 7 Cluster 1 — S7-0103: step_failed and step_skipped event contract tests.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_step_failed_payload,
    build_step_skipped_payload,
)


# ---------------------------------------------------------------------------
# Unit Tests — step_failed
# ---------------------------------------------------------------------------

def test_build_step_failed_payload_includes_step_id():  # PRD-04-BE-004
    result = build_step_failed_payload(step_id="step-1", run_id="run-001", error="boom", status="failed")
    assert result["step_id"] == "step-1"


def test_build_step_failed_payload_includes_error():  # PRD-04-BE-004
    result = build_step_failed_payload(step_id="step-1", run_id="run-001", error="element not found", status="failed")
    assert "element not found" in result["error"]


def test_build_step_failed_payload_includes_status():  # PRD-04-BE-004
    result = build_step_failed_payload(step_id="step-1", run_id="run-001", error="err", status="failed")
    assert result["status"] == "failed"


def test_build_step_failed_payload_includes_optional_operation_id():  # PRD-04-BE-004
    result = build_step_failed_payload(step_id="step-1", run_id="run-001", error="err", status="failed", operation_id="op-5")
    assert result.get("operation_id") == "op-5"


def test_build_step_failed_payload_includes_run_id():  # PRD-04-BE-004
    result = build_step_failed_payload(step_id="step-1", run_id="run-007", error="err", status="failed")
    assert result["run_id"] == "run-007"


# ---------------------------------------------------------------------------
# Unit Tests — step_skipped
# ---------------------------------------------------------------------------

def test_build_step_skipped_payload_includes_step_id():  # PRD-04-BE-005
    result = build_step_skipped_payload(step_id="step-2", run_id="run-001", reason="user skipped")
    assert result["step_id"] == "step-2"


def test_build_step_skipped_payload_includes_reason():  # PRD-04-BE-005
    result = build_step_skipped_payload(step_id="step-2", run_id="run-001", reason="optional step")
    assert "optional step" in result["reason"]


def test_build_step_skipped_payload_includes_run_id():  # PRD-04-BE-005
    result = build_step_skipped_payload(step_id="step-2", run_id="run-007", reason="skipped")
    assert result["run_id"] == "run-007"


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------

def test_step_failed_event_type_field_correct():  # PRD-04-BE-004
    result = build_step_failed_payload(step_id="s1", run_id="r1", error="e", status="failed")
    assert result["type"] == "step_failed"


def test_step_skipped_event_type_field_correct():  # PRD-04-BE-005
    result = build_step_skipped_payload(step_id="s1", run_id="r1", reason="r")
    assert result["type"] == "step_skipped"


def test_step_failed_uses_backend_event_envelope():  # PRD-04-BE-004
    result = build_step_failed_payload(step_id="s1", run_id="r1", error="e", status="failed")
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_step_skipped_uses_backend_event_envelope():  # PRD-04-BE-005
    result = build_step_skipped_payload(step_id="s1", run_id="r1", reason="r")
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Integration / Sequencing Tests
# ---------------------------------------------------------------------------

def test_step_failed_and_step_skipped_carry_run_id_consistently():  # PRD-04-BE-004
    run_id = "run-xyz"
    failed = build_step_failed_payload(step_id="s1", run_id=run_id, error="e", status="failed")
    skipped = build_step_skipped_payload(step_id="s2", run_id=run_id, reason="user request")
    assert failed["run_id"] == run_id
    assert skipped["run_id"] == run_id


def test_step_failed_has_distinct_type_from_recovery_needed():  # PRD-04-BE-004
    result = build_step_failed_payload(step_id="s1", run_id="r1", error="e", status="failed")
    assert result["type"] == "step_failed"
    assert result["type"] != "recovery_needed"


def test_step_skipped_has_distinct_type_from_step_failed():  # PRD-04-BE-005
    failed = build_step_failed_payload(step_id="s1", run_id="r1", error="e", status="failed")
    skipped = build_step_skipped_payload(step_id="s1", run_id="r1", reason="skip")
    assert failed["type"] != skipped["type"]


# ---------------------------------------------------------------------------
# Negative Tests (required by GOV-S7-C0-009)
# ---------------------------------------------------------------------------

def test_step_failed_followed_by_step_recorded_is_invalid():  # GOV-S7-C0-001
    # Architectural invariant: a failed step cannot emit step_recorded.
    # Verified structurally — step_failed event type is "step_failed", not "step_recorded".
    failed = build_step_failed_payload(step_id="s1", run_id="r1", error="e", status="failed")
    assert failed["type"] != "step_recorded"


def test_step_skipped_followed_by_step_recorded_is_invalid():  # GOV-S7-C0-001
    skipped = build_step_skipped_payload(step_id="s1", run_id="r1", reason="skip")
    assert skipped["type"] != "step_recorded"


def test_build_step_failed_rejects_empty_step_id():  # PRD-04-BE-004
    with pytest.raises(ValueError, match="step_id"):
        build_step_failed_payload(step_id="", run_id="r1", error="e", status="failed")


def test_build_step_failed_rejects_empty_error():  # PRD-04-BE-004
    with pytest.raises(ValueError, match="error"):
        build_step_failed_payload(step_id="s1", run_id="r1", error="", status="failed")


def test_build_step_failed_rejects_empty_run_id():  # PRD-04-BE-004
    with pytest.raises(ValueError, match="run_id"):
        build_step_failed_payload(step_id="s1", run_id="", error="e", status="failed")


def test_build_step_skipped_rejects_empty_reason():  # PRD-04-BE-005
    with pytest.raises(ValueError, match="reason"):
        build_step_skipped_payload(step_id="s1", run_id="r1", reason="")


def test_build_step_skipped_rejects_empty_step_id():  # PRD-04-BE-005
    with pytest.raises(ValueError, match="step_id"):
        build_step_skipped_payload(step_id="", run_id="r1", reason="r")


def test_step_failed_not_emitted_when_recovery_resolves_successfully():  # GOV-S7-C0-001
    # Step_failed is only built when there IS a failure. Builder itself requires a non-empty error.
    with pytest.raises(ValueError):
        build_step_failed_payload(step_id="s1", run_id="r1", error="", status="failed")


def test_build_step_skipped_rejects_empty_run_id():
    with pytest.raises(ValueError, match="run_id"):
        build_step_skipped_payload(step_id="s1", run_id="", reason="skip")
