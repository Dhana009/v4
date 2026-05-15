"""
runtime/context_gates.py

Sufficiency gates for all major LLM runtime purpose families.

Source rule: Runtime Policy Spec — sufficiency gates exist for major purpose families.
Gates fail → ask_user, not auto-escalate to L5.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# GateResult
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    passed: bool
    failed_gate: str | None = None
    clarification_message: str | None = None
    action: str = "proceed"  # "proceed" | "ask_user"


# ---------------------------------------------------------------------------
# Gate clarification messages
# ---------------------------------------------------------------------------

GATE_CLARIFICATIONS: dict[str, str] = {
    "goal_clarity": "Could you rephrase your intention in one sentence?",
    "page_state_known": "Could you describe the current page state?",
    "page_intelligence_available": "Could you describe the current page structure?",
    "target_pages_available": "Which pages must the journey visit?",
    "step_ids_available": "What are the target step IDs?",
    "page_state_snapshot": "Could you describe the page you are on?",
    "validation_result_available": "What element are you trying to find?",
    "failure_evidence_available": "What went wrong? Please describe the failure.",
    "replay_failure_available": "What replay failure occurred?",
    "original_trace_available": "Please provide the original recorded trace.",
    "error_context_available": "Please describe the error context.",
    "assertion_result_available": "What is the current assertion result?",
}


# ---------------------------------------------------------------------------
# Gate definitions per purpose family
# ---------------------------------------------------------------------------

def _has_goal(ctx: dict[str, Any]) -> bool:
    goal = ctx.get("user_goal")
    return isinstance(goal, str) and len(goal.strip()) > 0


def _has_page_state(ctx: dict[str, Any]) -> bool:
    return ctx.get("page_state") is not None


def _has_page_intelligence(ctx: dict[str, Any]) -> bool:
    return ctx.get("page_intelligence") is not None


def _has_target_pages(ctx: dict[str, Any]) -> bool:
    pages = ctx.get("target_pages")
    return isinstance(pages, (list, tuple)) and len(pages) > 0


def _has_step_ids(ctx: dict[str, Any]) -> bool:
    ids = ctx.get("step_ids")
    return isinstance(ids, (list, tuple)) and len(ids) > 0


def _has_page_state_snapshot(ctx: dict[str, Any]) -> bool:
    return ctx.get("page_state") is not None


def _has_validation_result(ctx: dict[str, Any]) -> bool:
    return ctx.get("validation_result") is not None


def _has_failure_evidence(ctx: dict[str, Any]) -> bool:
    return ctx.get("failure_evidence") is not None


def _has_replay_failure(ctx: dict[str, Any]) -> bool:
    return ctx.get("replay_failure") is not None


def _has_original_trace(ctx: dict[str, Any]) -> bool:
    return ctx.get("original_trace") is not None


def _has_error_context(ctx: dict[str, Any]) -> bool:
    return ctx.get("error_context") is not None


def _has_assertion_result(ctx: dict[str, Any]) -> bool:
    return ctx.get("assertion_result") is not None


# Each entry: list of (gate_name, gate_fn)
SUFFICIENCY_GATES: dict[str, list[tuple[str, Callable[[dict[str, Any]], bool]]]] = {
    "intent_classifier": [
        ("goal_clarity", _has_goal),
    ],
    "clarification_generator": [
        ("goal_clarity", _has_goal),
    ],
    "page_validation_recommender": [
        ("page_state_known", _has_page_state),
        ("page_intelligence_available", _has_page_intelligence),
    ],
    "journey_planner": [
        ("target_pages_available", _has_target_pages),
    ],
    "step_plan_normalizer": [
        ("step_ids_available", _has_step_ids),
        ("page_state_snapshot", _has_page_state_snapshot),
    ],
    "locator_specialist": [
        ("validation_result_available", _has_validation_result),
    ],
    "recovery_diagnoser": [
        ("failure_evidence_available", _has_failure_evidence),
    ],
    "replay_repair_specialist": [
        ("original_trace_available", _has_original_trace),
        ("replay_failure_available", _has_replay_failure),
    ],
    "custom_assertion_planner": [
        ("assertion_result_available", _has_assertion_result),
    ],
    "recovery_diagnoser": [
        ("failure_evidence_available", _has_failure_evidence),
    ],
}


# ---------------------------------------------------------------------------
# Gate checker
# ---------------------------------------------------------------------------

def check_gates(purpose_id: str, context: dict[str, Any]) -> GateResult:
    """Check all sufficiency gates for *purpose_id* against *context*.

    Returns GateResult with passed=True if all gates pass,
    or passed=False with the first failed gate name + clarification.
    """
    gates = SUFFICIENCY_GATES.get(purpose_id, [])
    for gate_name, gate_fn in gates:
        if not gate_fn(context):
            message = GATE_CLARIFICATIONS.get(gate_name, "Could you provide more information?")
            return GateResult(
                passed=False,
                failed_gate=gate_name,
                clarification_message=message,
                action="ask_user",
            )
    return GateResult(passed=True, action="proceed")
