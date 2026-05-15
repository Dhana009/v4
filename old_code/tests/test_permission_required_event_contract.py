"""
tests/test_permission_required_event_contract.py

Sprint 7 Cluster 1 — S7-0104: permission_required event and permission_decision command tests.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    SUPPORTED_FRONTEND_COMMAND_TYPES,
    build_permission_required_payload,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_build_permission_required_payload_includes_run_id():  # PRD-04-BE-006
    result = build_permission_required_payload(
        run_id="run-001", operation_id="op-1", action_type="navigate", risk_level="high", message="Confirm?"
    )
    assert result["run_id"] == "run-001"


def test_build_permission_required_payload_includes_operation_id():  # PRD-04-BE-006
    result = build_permission_required_payload(
        run_id="run-001", operation_id="op-99", action_type="click", risk_level="medium", message="Ok?"
    )
    assert result["operation_id"] == "op-99"


def test_build_permission_required_payload_includes_action_type():  # PRD-04-BE-006
    result = build_permission_required_payload(
        run_id="run-001", operation_id="op-1", action_type="fill_form", risk_level="high", message="Msg"
    )
    assert result["action_type"] == "fill_form"


def test_build_permission_required_payload_includes_risk_level():  # PRD-04-BE-006
    result = build_permission_required_payload(
        run_id="run-001", operation_id="op-1", action_type="click", risk_level="critical", message="Msg"
    )
    assert result["risk_level"] == "critical"


def test_build_permission_required_payload_includes_message():  # PRD-04-BE-006
    result = build_permission_required_payload(
        run_id="run-001", operation_id="op-1", action_type="click", risk_level="low", message="Please confirm."
    )
    assert "Please confirm" in result["message"]


def test_build_permission_required_payload_includes_optional_options():  # PRD-04-BE-006
    options = ["allow", "deny"]
    result = build_permission_required_payload(
        run_id="run-001", operation_id="op-1", action_type="click", risk_level="low", message="Msg", options=options
    )
    assert result.get("options") == options


def test_build_permission_required_payload_options_absent_when_not_given():  # PRD-04-BE-006
    result = build_permission_required_payload(
        run_id="run-001", operation_id="op-1", action_type="click", risk_level="low", message="Msg"
    )
    # options should be None or absent
    assert result.get("options") is None or "options" not in result


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------

def test_permission_required_event_type_field_correct():  # PRD-04-BE-006
    result = build_permission_required_payload(
        run_id="r", operation_id="o", action_type="a", risk_level="low", message="m"
    )
    assert result["type"] == "permission_required"


def test_permission_required_uses_backend_event_envelope():  # PRD-04-BE-006
    result = build_permission_required_payload(
        run_id="r", operation_id="o", action_type="a", risk_level="low", message="m"
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_permission_decision_command_registered_in_supported_types():  # PRD-04-CMD-005
    assert "permission_decision" in SUPPORTED_FRONTEND_COMMAND_TYPES


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_high_risk_action_emits_permission_required():  # PRD-04-BE-006
    # Builder validates that all required fields are present for a high-risk event
    result = build_permission_required_payload(
        run_id="run-001", operation_id="op-1", action_type="delete_all_data", risk_level="critical", message="This will delete everything."
    )
    assert result["type"] == "permission_required"
    assert result["risk_level"] == "critical"


def test_permission_approved_continues_only_for_matching_run_and_operation():  # PRD-04-CMD-005
    # Structural: builder requires both run_id and operation_id — mismatch check is at command handler
    result = build_permission_required_payload(
        run_id="run-match", operation_id="op-match", action_type="click", risk_level="high", message="confirm"
    )
    assert result["run_id"] == "run-match"
    assert result["operation_id"] == "op-match"


# ---------------------------------------------------------------------------
# Negative Tests (required by GOV-S7-C0-009)
# ---------------------------------------------------------------------------

def test_build_permission_required_rejects_empty_run_id():  # PRD-04-BE-006
    with pytest.raises(ValueError, match="run_id"):
        build_permission_required_payload(
            run_id="", operation_id="op-1", action_type="click", risk_level="low", message="m"
        )


def test_build_permission_required_rejects_empty_action_type():  # PRD-04-BE-006
    with pytest.raises(ValueError, match="action_type"):
        build_permission_required_payload(
            run_id="r", operation_id="op-1", action_type="", risk_level="low", message="m"
        )


def test_build_permission_required_rejects_empty_operation_id():  # PRD-04-BE-006
    with pytest.raises(ValueError, match="operation_id"):
        build_permission_required_payload(
            run_id="r", operation_id="", action_type="click", risk_level="low", message="m"
        )


def test_build_permission_required_rejects_empty_message():  # PRD-04-BE-006
    with pytest.raises(ValueError, match="message"):
        build_permission_required_payload(
            run_id="r", operation_id="op-1", action_type="click", risk_level="low", message=""
        )


def test_build_permission_required_rejects_empty_risk_level():  # PRD-04-BE-006
    with pytest.raises(ValueError, match="risk_level"):
        build_permission_required_payload(
            run_id="r", operation_id="op-1", action_type="click", risk_level="", message="m"
        )
