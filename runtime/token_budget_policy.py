"""
runtime/token_budget_policy.py

Token budget enforcement and telemetry for all LLM runtime purposes.

Source rule: Runtime Policy Spec — token budget enforced per purpose.
Budget exceeded → compact context or ask_user, not silent truncation.
All calls logged with purpose/model/tokens.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Per-purpose token budgets (input tokens max)
# ---------------------------------------------------------------------------

PURPOSE_TOKEN_BUDGETS: dict[str, int] = {
    "intent_classifier": 500,
    "clarification_generator": 500,
    "page_intelligence_summarizer": 1400,
    "page_validation_recommender": 1500,
    "journey_planner": 2000,
    "step_plan_normalizer": 2000,
    "plan_diff_editor": 2200,
    "locator_specialist": 2200,
    "custom_assertion_planner": 2200,
    "execution_driver": 500,
    "recovery_diagnoser": 1500,
    "replay_repair_specialist": 1800,
    "user_response_writer": 500,
    "trace_summarizer": 1000,
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class BudgetResult:
    action: str          # "proceed" | "compact" | "ask_clarification" | "fail_closed"
    enforced: bool = True
    budget: int = 0
    context_tokens: int = 0
    overage: int = 0


@dataclass
class TelemetryRecord:
    purpose: str
    model: str
    context_level: str
    context_tokens: int
    total_input_tokens: int
    output_tokens: int
    latency_ms: int
    finish_reason: str
    schema_validation: str
    result: str


# ---------------------------------------------------------------------------
# Telemetry log
# ---------------------------------------------------------------------------

_telemetry_log: list[dict[str, Any]] = []


def clear_telemetry_log() -> None:
    _telemetry_log.clear()


def get_telemetry_log() -> list[dict[str, Any]]:
    return list(_telemetry_log)


def record_llm_call_telemetry(record: TelemetryRecord) -> None:
    """Append a telemetry record to the log."""
    _telemetry_log.append({
        "purpose": record.purpose,
        "model": record.model,
        "context_level": record.context_level,
        "context_tokens": record.context_tokens,
        "total_input_tokens": record.total_input_tokens,
        "output_tokens": record.output_tokens,
        "latency_ms": record.latency_ms,
        "finish_reason": record.finish_reason,
        "schema_validation": record.schema_validation,
        "result": record.result,
    })


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------

# Purposes that cannot be escalated (no ask_user allowed on budget exceed)
_NO_ESCALATION_PURPOSES: frozenset[str] = frozenset({
    "page_intelligence_summarizer",
    "trace_summarizer",
    "execution_driver",
})


def check_and_enforce_budget(
    purpose_id: str,
    context_tokens: int,
    can_compact: bool = True,
) -> BudgetResult:
    """Check *context_tokens* against the budget for *purpose_id*.

    Returns BudgetResult with action:
      "proceed"           — within budget
      "compact"           — over budget but compaction possible
      "ask_clarification" — over budget, cannot compact, escalation allowed
      "fail_closed"       — over budget, cannot compact, no escalation
    """
    budget = PURPOSE_TOKEN_BUDGETS.get(purpose_id)
    if budget is None:
        raise ValueError(f"Unknown purpose_id: {purpose_id!r}")

    if context_tokens <= budget:
        return BudgetResult(
            action="proceed",
            enforced=True,
            budget=budget,
            context_tokens=context_tokens,
            overage=0,
        )

    overage = context_tokens - budget

    # Log budget exceeded
    _telemetry_log.append({
        "event": "budget_exceeded",
        "purpose": purpose_id,
        "budget": budget,
        "context_tokens": context_tokens,
        "overage": overage,
    })

    # Try compaction first
    if can_compact:
        return BudgetResult(
            action="compact",
            enforced=True,
            budget=budget,
            context_tokens=context_tokens,
            overage=overage,
        )

    # Cannot compact — check if escalation allowed
    if purpose_id in _NO_ESCALATION_PURPOSES:
        return BudgetResult(
            action="fail_closed",
            enforced=True,
            budget=budget,
            context_tokens=context_tokens,
            overage=overage,
        )

    return BudgetResult(
        action="ask_clarification",
        enforced=True,
        budget=budget,
        context_tokens=context_tokens,
        overage=overage,
    )
