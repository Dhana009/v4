from __future__ import annotations

import pytest

from runtime.recovery_manager import RecoveryManager, classify_failure


@pytest.mark.parametrize("tool_name", ["action_assert", "action_click"])
def test_recoverable_execution_failures_return_recover_and_purge_flags(tool_name: str) -> None:
    decision = RecoveryManager().classify_failure(
        tool_name,
        step_id="step-1",
        result={"success": False, "error": f"{tool_name} failed"},
    )

    assert decision.outcome == "recover"
    assert decision.stop_batch is True
    assert decision.purge_step_id == "step-1"
    assert decision.clear_last_successful_action is True
    assert decision.clear_step_success_history is True
    assert decision.clear_last_action_context is True
    assert decision.next_phase == "recovery"
    assert decision.requires_replan is True
    assert decision.reason == f"{tool_name} failed"


def test_locator_validate_invalid_is_advisory_and_does_not_recover() -> None:
    decision = classify_failure(
        "locator_validate",
        step_id="step-1",
        result={"valid": False, "count": 0},
    )

    assert decision.outcome == "skip"
    assert decision.stop_batch is False
    assert decision.purge_step_id is None
    assert decision.clear_last_successful_action is False
    assert decision.clear_step_success_history is False
    assert decision.clear_last_action_context is False
    assert decision.next_phase is None
    assert decision.requires_replan is False
    assert decision.reason == "locator_validate invalid remains advisory in v1"
