from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RecoveryOutcome = Literal["recover", "ask_user", "skip", "stop"]
RecoveryPhase = Literal["recovery", "failed"]

RECOVERABLE_FAILURE_TOOLS = {
    "action_click",
    "action_fill",
    "action_assert",
    "page_navigate",
    "page_go_back",
    "page_go_forward",
    "page_reload",
    "scroll_into_view",
}


@dataclass(slots=True)
class RecoveryDecision:
    outcome: RecoveryOutcome
    stop_batch: bool
    purge_step_id: str | None
    clear_last_successful_action: bool
    clear_step_success_history: bool
    clear_last_action_context: bool
    next_phase: RecoveryPhase | None
    requires_replan: bool
    reason: str


class RecoveryManager:
    def classify_failure(
        self,
        tool_name: str,
        *,
        step_id: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> RecoveryDecision:
        normalized_tool_name = str(tool_name or "").strip()
        normalized_step_id = str(step_id or "").strip() or None
        normalized_result = result if isinstance(result, dict) else {}
        skipped = bool(normalized_result.get("skipped"))

        if normalized_tool_name == "locator_validate" and normalized_result.get("valid") is False:
            return RecoveryDecision(
                outcome="skip",
                stop_batch=False,
                purge_step_id=None,
                clear_last_successful_action=False,
                clear_step_success_history=False,
                clear_last_action_context=False,
                next_phase=None,
                requires_replan=False,
                reason="locator_validate invalid remains advisory in v1",
            )

        if normalized_tool_name in RECOVERABLE_FAILURE_TOOLS and not skipped:
            failure_reason = str(normalized_result.get("error") or "").strip()
            if not failure_reason:
                failure_reason = f"{normalized_tool_name} failure"
            return RecoveryDecision(
                outcome="recover",
                stop_batch=True,
                purge_step_id=normalized_step_id,
                clear_last_successful_action=True,
                clear_step_success_history=True,
                clear_last_action_context=True,
                next_phase="recovery",
                requires_replan=True,
                reason=failure_reason,
            )

        if skipped:
            return RecoveryDecision(
                outcome="skip",
                stop_batch=False,
                purge_step_id=None,
                clear_last_successful_action=False,
                clear_step_success_history=False,
                clear_last_action_context=False,
                next_phase=None,
                requires_replan=False,
                reason=str(normalized_result.get("reason") or "tool call skipped"),
            )

        failure_reason = str(normalized_result.get("error") or "").strip()
        if not failure_reason:
            failure_reason = f"{normalized_tool_name or 'tool'} failure"
        return RecoveryDecision(
            outcome="stop",
            stop_batch=True,
            purge_step_id=normalized_step_id,
            clear_last_successful_action=False,
            clear_step_success_history=False,
            clear_last_action_context=False,
            next_phase="failed",
            requires_replan=True,
            reason=failure_reason,
        )


def classify_failure(
    tool_name: str,
    *,
    step_id: str | None = None,
    result: dict[str, Any] | None = None,
) -> RecoveryDecision:
    return RecoveryManager().classify_failure(
        tool_name,
        step_id=step_id,
        result=result,
    )
