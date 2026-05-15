"""
tests/test_recovery_needed_event.py

Sprint 7 Cluster 2 — S7-0206: recovery_diagnoser frontend-facing payload alignment.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_recovery_needed_structured_event,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_recovery_needed_structured_type_correct():  # S7-0206
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="element not found",
        options=[{"id": "o1", "label": "Retry", "action": "retry"}],
    )
    assert result["type"] == "recovery_needed"


def test_recovery_needed_structured_includes_run_id():  # S7-0206
    result = build_recovery_needed_structured_event(
        run_id="run-abc",
        step_id="step-1",
        failure_reason="timeout",
        options=[{"id": "o1", "label": "Retry", "action": "retry"}],
    )
    assert result["run_id"] == "run-abc"


def test_recovery_needed_structured_includes_step_id():  # S7-0206
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-xyz",
        failure_reason="element not found",
        options=[{"id": "o1", "label": "Retry", "action": "retry"}],
    )
    assert result["step_id"] == "step-xyz"


def test_recovery_needed_structured_includes_failure_reason():  # S7-0206
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="click target not visible",
        options=[{"id": "o1", "label": "Skip", "action": "skip"}],
    )
    assert "click target not visible" in result["failure_reason"]


def test_recovery_needed_structured_includes_options():  # S7-0206
    options = [
        {"id": "o1", "label": "Retry", "action": "retry", "description": "Retry step"},
        {"id": "o2", "label": "Skip", "action": "skip", "description": "Skip step"},
        {"id": "o3", "label": "Stop", "action": "stop", "description": "Stop run"},
    ]
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="error",
        options=options,
    )
    assert len(result["options"]) == 3


def test_recovery_needed_structured_options_have_required_fields():  # S7-0206
    options = [{"id": "o1", "label": "Retry", "action": "retry"}]
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="error",
        options=options,
    )
    opt = result["options"][0]
    for field in ("id", "label", "action"):
        assert field in opt, f"option missing field: {field}"


def test_recovery_needed_structured_uses_backend_envelope():  # S7-0206
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="error",
        options=[{"id": "o1", "label": "Retry", "action": "retry"}],
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_recovery_needed_structured_schema_version():  # GOV-S7-C0-007
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="error",
        options=[{"id": "o1", "label": "Retry", "action": "retry"}],
    )
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_recovery_needed_includes_expected_actual_when_given():  # S7-0206
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="assertion failed",
        options=[{"id": "o1", "label": "Retry", "action": "retry"}],
        expected="visible",
        actual="hidden",
    )
    assert result.get("expected") == "visible"
    assert result.get("actual") == "hidden"


# ---------------------------------------------------------------------------
# Contract Tests — unresolved blocks completion
# ---------------------------------------------------------------------------

def test_recovery_needed_does_not_imply_run_completed():  # S7-0206
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="error",
        options=[{"id": "o1", "label": "Retry", "action": "retry"}],
    )
    assert result["type"] != "run_completed"
    assert result["type"] != "step_recorded"


def test_recovery_needed_options_are_explicit_and_typed():  # S7-0206
    result = build_recovery_needed_structured_event(
        run_id="run-1",
        step_id="step-1",
        failure_reason="error",
        options=[
            {"id": "o1", "label": "Retry", "action": "retry"},
            {"id": "o2", "label": "Skip", "action": "skip"},
        ],
    )
    actions = [o["action"] for o in result["options"]]
    assert all(a in {"retry", "skip", "stop"} for a in actions)


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_recovery_needed_structured_rejects_empty_run_id():  # S7-0206
    with pytest.raises(ValueError, match="run_id"):
        build_recovery_needed_structured_event(
            run_id="",
            step_id="step-1",
            failure_reason="error",
            options=[{"id": "o1", "label": "Retry", "action": "retry"}],
        )


def test_recovery_needed_structured_rejects_empty_step_id():  # S7-0206
    with pytest.raises(ValueError, match="step_id"):
        build_recovery_needed_structured_event(
            run_id="run-1",
            step_id="",
            failure_reason="error",
            options=[{"id": "o1", "label": "Retry", "action": "retry"}],
        )


def test_recovery_needed_structured_rejects_empty_failure_reason():  # S7-0206
    with pytest.raises(ValueError, match="failure_reason"):
        build_recovery_needed_structured_event(
            run_id="run-1",
            step_id="step-1",
            failure_reason="",
            options=[{"id": "o1", "label": "Retry", "action": "retry"}],
        )


def test_recovery_needed_structured_rejects_empty_options():  # S7-0206
    with pytest.raises(ValueError, match="options"):
        build_recovery_needed_structured_event(
            run_id="run-1",
            step_id="step-1",
            failure_reason="error",
            options=[],
        )


def test_recovery_needed_structured_rejects_none_options():  # S7-0206
    with pytest.raises((ValueError, TypeError)):
        build_recovery_needed_structured_event(
            run_id="run-1",
            step_id="step-1",
            failure_reason="error",
            options=None,  # type: ignore
        )
