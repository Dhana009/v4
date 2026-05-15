from __future__ import annotations

"""Extended contract tests for runtime/recovery_manager.py.

Covers all classification branches: recover, skip, stop, advisory locator,
skipped tool, unknown tool, missing step_id, missing result.
"""

import pytest

from runtime.recovery_manager import (
    RECOVERABLE_FAILURE_TOOLS,
    RecoveryDecision,
    RecoveryManager,
    classify_failure,
)


# ---------------------------------------------------------------------------
# All recoverable tools trigger recover outcome
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool_name", sorted(RECOVERABLE_FAILURE_TOOLS))
def test_all_recoverable_tools_return_recover_outcome(tool_name: str) -> None:
    decision = classify_failure(
        tool_name,
        step_id="step-1",
        result={"success": False, "error": f"{tool_name} timed out"},
    )
    assert decision.outcome == "recover"
    assert decision.stop_batch is True
    assert decision.next_phase == "recovery"
    assert decision.requires_replan is True
    assert decision.clear_last_successful_action is True
    assert decision.clear_step_success_history is True
    assert decision.clear_last_action_context is True


# ---------------------------------------------------------------------------
# Recoverable tool with no error message falls back to default reason
# ---------------------------------------------------------------------------

def test_recoverable_tool_without_error_message_uses_default_reason() -> None:
    decision = classify_failure("action_click", step_id="step-1", result={"success": False})
    assert decision.outcome == "recover"
    assert decision.reason == "action_click failure"


# ---------------------------------------------------------------------------
# Skipped tool result → skip outcome regardless of tool name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool_name", ["action_click", "action_fill", "page_navigate", "browser_get_state"])
def test_skipped_result_returns_skip_outcome(tool_name: str) -> None:
    decision = classify_failure(tool_name, step_id="step-1", result={"success": True, "skipped": True})
    assert decision.outcome == "skip"
    assert decision.stop_batch is False
    assert decision.purge_step_id is None
    assert decision.next_phase is None
    assert decision.requires_replan is False


def test_skipped_result_preserves_skip_reason() -> None:
    decision = classify_failure(
        "action_click",
        step_id="step-1",
        result={"success": True, "skipped": True, "reason": "step already completed"},
    )
    assert decision.outcome == "skip"
    assert "already completed" in decision.reason


def test_skipped_result_without_reason_uses_default() -> None:
    decision = classify_failure("action_fill", result={"skipped": True})
    assert decision.outcome == "skip"
    assert decision.reason  # non-empty


# ---------------------------------------------------------------------------
# locator_validate invalid → advisory skip (not recover)
# ---------------------------------------------------------------------------

def test_locator_validate_invalid_is_advisory_skip_not_recover() -> None:
    decision = classify_failure("locator_validate", result={"valid": False, "count": 0})
    assert decision.outcome == "skip"
    assert decision.stop_batch is False
    assert decision.requires_replan is False
    assert decision.next_phase is None


def test_locator_validate_does_not_clear_action_history() -> None:
    decision = classify_failure("locator_validate", result={"valid": False})
    assert decision.clear_last_successful_action is False
    assert decision.clear_step_success_history is False
    assert decision.clear_last_action_context is False


# ---------------------------------------------------------------------------
# Unknown / non-recoverable tool → stop outcome
# ---------------------------------------------------------------------------

def test_unknown_tool_returns_stop_outcome() -> None:
    decision = classify_failure("unknown_tool", step_id="step-1", result={"success": False, "error": "crash"})
    assert decision.outcome == "stop"
    assert decision.stop_batch is True
    assert decision.next_phase == "failed"
    assert decision.requires_replan is True


def test_non_execution_tool_returns_stop_not_recover() -> None:
    decision = classify_failure("browser_get_state", step_id="step-1", result={"success": False})
    assert decision.outcome == "stop"


# ---------------------------------------------------------------------------
# step_id propagation
# ---------------------------------------------------------------------------

def test_purge_step_id_matches_provided_step_id() -> None:
    decision = classify_failure("action_click", step_id="step-42", result={"success": False})
    assert decision.purge_step_id == "step-42"


def test_missing_step_id_results_in_none_purge() -> None:
    decision = classify_failure("action_click", result={"success": False})
    assert decision.purge_step_id is None


# ---------------------------------------------------------------------------
# None / empty result handled gracefully
# ---------------------------------------------------------------------------

def test_none_result_does_not_crash() -> None:
    decision = classify_failure("action_click", step_id="step-1", result=None)
    assert decision.outcome in {"recover", "skip", "stop"}


def test_empty_result_does_not_crash() -> None:
    decision = classify_failure("page_navigate", step_id="step-1", result={})
    assert decision.outcome in {"recover", "skip", "stop"}


def test_empty_tool_name_returns_stop() -> None:
    decision = classify_failure("", step_id="step-1", result={"success": False})
    assert decision.outcome == "stop"


# ---------------------------------------------------------------------------
# RecoveryDecision is a dataclass with expected fields
# ---------------------------------------------------------------------------

def test_recovery_decision_has_all_required_fields() -> None:
    decision = classify_failure("action_click", step_id="step-1", result={"success": False})
    assert hasattr(decision, "outcome")
    assert hasattr(decision, "stop_batch")
    assert hasattr(decision, "purge_step_id")
    assert hasattr(decision, "clear_last_successful_action")
    assert hasattr(decision, "clear_step_success_history")
    assert hasattr(decision, "clear_last_action_context")
    assert hasattr(decision, "next_phase")
    assert hasattr(decision, "requires_replan")
    assert hasattr(decision, "reason")


# ---------------------------------------------------------------------------
# RecoveryManager instance vs module-level classify_failure are equivalent
# ---------------------------------------------------------------------------

def test_module_function_and_class_method_return_equivalent_result() -> None:
    kwargs = dict(tool_name="action_fill", step_id="step-1", result={"success": False, "error": "timeout"})
    mgr_decision = RecoveryManager().classify_failure(**kwargs)
    fn_decision = classify_failure(**kwargs)
    assert mgr_decision.outcome == fn_decision.outcome
    assert mgr_decision.reason == fn_decision.reason
    assert mgr_decision.next_phase == fn_decision.next_phase
