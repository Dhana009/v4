from __future__ import annotations

from copy import deepcopy

import pytest

from runtime.event_contracts import FRONTEND_COMMAND_SCHEMA_VERSION, normalize_frontend_command


def _normalize(command: dict[str, object], current_state: dict[str, object] | None = None):
    command_before = deepcopy(command)
    current_state_before = deepcopy(current_state) if current_state is not None else None

    normalized_command, rejection = normalize_frontend_command(command, current_state=current_state)

    assert command == command_before
    if current_state_before is not None:
        assert current_state == current_state_before

    return normalized_command, rejection


def test_missing_command_type_is_typed_rejected() -> None:
    command = {
        "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
        "command_id": "cmd-missing-type",
        "run_id": "run-old",
    }
    current_state = {
        "run_id": "run-current",
        "plan_id": "plan-current",
        "phase": "executing",
    }

    normalized_command, rejection = _normalize(command, current_state=current_state)

    assert normalized_command is None
    assert rejection is not None
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "MALFORMED_COMMAND"
    assert rejection["command_id"] == "cmd-missing-type"
    assert rejection["run_id"] == "run-current"
    assert "missing type" in rejection["detail"]
    assert rejection["current_state"]["run_id"] == "run-current"
    assert rejection["current_state"]["plan_id"] == "plan-current"


def test_incomplete_canonical_command_envelope_is_typed_rejected() -> None:
    command = {
        "type": "confirmed",
        "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
        "run_id": "run-old",
    }
    current_state = {
        "run_id": "run-current",
        "plan_id": "plan-current",
        "phase": "executing",
    }

    normalized_command, rejection = _normalize(command, current_state=current_state)

    assert normalized_command is None
    assert rejection is not None
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "MALFORMED_COMMAND"
    assert rejection["run_id"] == "run-current"
    assert "command envelope is incomplete" in rejection["detail"]
    assert rejection["current_state"]["run_id"] == "run-current"


def test_unknown_command_type_is_typed_rejected() -> None:
    command = {
        "type": "mystery_command",
        "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
        "command_id": "cmd-mystery",
        "run_id": "run-old",
    }
    current_state = {
        "run_id": "run-current",
        "plan_id": "plan-current",
        "phase": "executing",
    }

    normalized_command, rejection = _normalize(command, current_state=current_state)

    assert normalized_command is None
    assert rejection is not None
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "COMMAND_NOT_SUPPORTED"
    assert rejection["command_id"] == "cmd-mystery"
    assert rejection["run_id"] == "run-old"
    assert rejection["current_state"]["run_id"] == "run-current"
    assert "Unsupported command" in rejection["message"]


def test_unsupported_schema_version_is_typed_rejected() -> None:
    command = {
        "type": "confirmed",
        "schema_version": "autoworkbench.command.v9",
        "command_id": "cmd-bad-version",
        "run_id": "run-old",
    }
    current_state = {
        "run_id": "run-current",
        "plan_id": "plan-current",
        "phase": "executing",
    }

    normalized_command, rejection = _normalize(command, current_state=current_state)

    assert normalized_command is None
    assert rejection is not None
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "UNSUPPORTED_COMMAND_VERSION"
    assert rejection["command_id"] == "cmd-bad-version"
    assert rejection["run_id"] == "run-current"
    assert "version mismatch" in rejection["detail"]
    assert rejection["current_state"]["run_id"] == "run-current"


@pytest.mark.parametrize("command_type", ["confirmed", "correction"])
def test_stale_run_id_payload_does_not_mutate_current_state(
    command_type: str,
) -> None:
    command = {
        "type": command_type,
        "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
        "command_id": f"cmd-{command_type}",
        "run_id": "run-old",
        "plan_id": "plan-old",
        "message": "Use the newer plan",
    }
    current_state = {
        "run_id": "run-current",
        "plan_id": "plan-current",
        "phase": "executing",
        "context": {"nested": True},
    }

    normalized_command, rejection = _normalize(command, current_state=current_state)

    assert normalized_command is None
    assert rejection is not None
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "STALE_COMMAND"
    assert rejection["command_type"] == command_type
    assert rejection["command_id"] == f"cmd-{command_type}"
    assert rejection["run_id"] == "run-old"
    assert rejection["current_state"]["run_id"] == "run-current"
    assert rejection["current_state"]["plan_id"] == "plan-current"
    assert rejection["current_state"]["context"] == {"nested": True}
    assert "run_id" in rejection["detail"]
