"""
tests/test_step_progress_events_contract.py

Sprint 7 Cluster 1 — S7-0102: step_validating and step_executing event contract tests.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_step_executing_payload,
    build_step_validating_payload,
)


# ---------------------------------------------------------------------------
# Unit Tests — step_validating
# ---------------------------------------------------------------------------

def test_build_step_validating_payload_includes_step_id():  # PRD-04-BE-002
    result = build_step_validating_payload(step_id="step-1", run_id="run-001")
    assert result["step_id"] == "step-1"


def test_build_step_validating_payload_includes_run_id():  # PRD-04-BE-002
    result = build_step_validating_payload(step_id="step-1", run_id="run-001")
    assert result["run_id"] == "run-001"


def test_build_step_validating_payload_includes_optional_operation_id():  # PRD-04-BE-002
    result = build_step_validating_payload(step_id="step-1", run_id="run-001", operation_id="op-99")
    assert result.get("operation_id") == "op-99"


def test_build_step_validating_payload_operation_id_absent_when_not_given():  # PRD-04-BE-002
    result = build_step_validating_payload(step_id="step-1", run_id="run-001")
    assert result.get("operation_id") is None or "operation_id" not in result


def test_build_step_validating_payload_includes_optional_locator():  # PRD-04-BE-002
    result = build_step_validating_payload(step_id="step-1", run_id="run-001", locator="#btn")
    assert result.get("locator") == "#btn"


# ---------------------------------------------------------------------------
# Unit Tests — step_executing
# ---------------------------------------------------------------------------

def test_build_step_executing_payload_includes_step_id():  # PRD-04-BE-003
    result = build_step_executing_payload(step_id="step-1", run_id="run-001", action="click")
    assert result["step_id"] == "step-1"


def test_build_step_executing_payload_includes_action():  # PRD-04-BE-003
    result = build_step_executing_payload(step_id="step-1", run_id="run-001", action="fill_input")
    assert result["action"] == "fill_input"


def test_build_step_executing_payload_includes_run_id():  # PRD-04-BE-003
    result = build_step_executing_payload(step_id="step-1", run_id="run-001", action="click")
    assert result["run_id"] == "run-001"


def test_build_step_executing_payload_includes_optional_operation_id():  # PRD-04-BE-003
    result = build_step_executing_payload(step_id="step-1", run_id="run-001", action="click", operation_id="op-7")
    assert result.get("operation_id") == "op-7"


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------

def test_step_validating_event_type_field_correct():  # PRD-04-BE-002
    result = build_step_validating_payload(step_id="step-1", run_id="run-001")
    assert result["type"] == "step_validating"


def test_step_executing_event_type_field_correct():  # PRD-04-BE-003
    result = build_step_executing_payload(step_id="step-1", run_id="run-001", action="click")
    assert result["type"] == "step_executing"


def test_step_validating_uses_backend_event_envelope():  # PRD-04-BE-002
    result = build_step_validating_payload(step_id="step-1", run_id="run-001")
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_step_executing_uses_backend_event_envelope():  # PRD-04-BE-003
    result = build_step_executing_payload(step_id="step-1", run_id="run-001", action="click")
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Integration Tests — ordering invariants
# ---------------------------------------------------------------------------

def test_step_progress_events_include_consistent_run_id():  # PRD-04-BE-001
    run_id = "run-consistent"
    val = build_step_validating_payload(step_id="s1", run_id=run_id)
    exe = build_step_executing_payload(step_id="s1", run_id=run_id, action="click")
    assert val["run_id"] == run_id
    assert exe["run_id"] == run_id


def test_step_validating_and_executing_carry_same_step_id():  # PRD-04-BE-002
    step_id = "step-ordered"
    val = build_step_validating_payload(step_id=step_id, run_id="run-001")
    exe = build_step_executing_payload(step_id=step_id, run_id="run-001", action="navigate")
    assert val["step_id"] == exe["step_id"] == step_id


# ---------------------------------------------------------------------------
# Negative Tests (required by GOV-S7-C0-009)
# ---------------------------------------------------------------------------

def test_build_step_validating_rejects_empty_step_id():  # PRD-04-BE-002
    with pytest.raises(ValueError, match="step_id"):
        build_step_validating_payload(step_id="", run_id="run-001")


def test_build_step_validating_rejects_empty_run_id():  # PRD-04-BE-002
    with pytest.raises(ValueError, match="run_id"):
        build_step_validating_payload(step_id="s1", run_id="")


def test_build_step_executing_rejects_empty_step_id():  # PRD-04-BE-003
    with pytest.raises(ValueError, match="step_id"):
        build_step_executing_payload(step_id="", run_id="run-001", action="click")


def test_build_step_executing_rejects_empty_action():  # PRD-04-BE-003
    with pytest.raises(ValueError, match="action"):
        build_step_executing_payload(step_id="s1", run_id="run-001", action="")


def test_build_step_executing_rejects_empty_run_id():  # PRD-04-BE-003
    with pytest.raises(ValueError, match="run_id"):
        build_step_executing_payload(step_id="s1", run_id="", action="click")


def test_step_executing_payload_is_json_safe():  # GOV-S7-C0-001
    import json
    result = build_step_executing_payload(step_id="s1", run_id="run-001", action="click")
    # Should not raise
    json.dumps(result)
