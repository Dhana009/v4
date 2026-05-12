"""
runtime/context_request_policy.py

Structured context request and escalation approval policy.

Source rule: Runtime Policy Spec — LLM context_request must include type/reason/scope.
Backend denies context request if purpose disallows escalation.
Backend denies broad/unscoped full DOM requests.
All escalations (approved + denied) are logged with reason.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from typing import Any

from runtime.context_levels import CONTEXT_LEVELS, is_within_ceiling, level_rank


# ---------------------------------------------------------------------------
# Per-purpose maximum allowed context level
# ---------------------------------------------------------------------------

PURPOSE_MAX_CONTEXT_LEVEL: dict[str, str] = {
    "intent_classifier": "L0",
    "clarification_generator": "L0",
    "page_intelligence_summarizer": "L2",
    "page_validation_recommender": "L3",
    "journey_planner": "L2",
    "step_plan_normalizer": "L2",
    "plan_diff_editor": "L2",
    "locator_specialist": "L3",
    "custom_assertion_planner": "L2",
    "execution_driver": "L1",
    "recovery_diagnoser": "L4",
    "replay_repair_specialist": "L4",
    "user_response_writer": "L0",
    "trace_summarizer": "L2",
}

# Scopes that are considered "broad" / unscoped (not allowed)
_BROAD_SCOPES: frozenset[str] = frozenset({
    "", "entire_page", "full_page", "whole_page", "all", "*", "everything",
})


# ---------------------------------------------------------------------------
# Escalation log
# ---------------------------------------------------------------------------

class EscalationLog:
    """Module-level escalation log — approved and denied entries."""

    _log: list[dict[str, Any]] = []

    @classmethod
    def append(cls, entry: dict[str, Any]) -> None:
        cls._log.append(entry)

    @classmethod
    def get_all(cls) -> list[dict[str, Any]]:
        return list(cls._log)

    @classmethod
    def clear(cls) -> None:
        cls._log.clear()


# Module-level reference (used by tests)
_escalation_log = EscalationLog


# ---------------------------------------------------------------------------
# Context request processor
# ---------------------------------------------------------------------------

def process_context_request(
    purpose_id: str,
    requested_type: str | None,
    reason: str | None,
    scope: str | None,
) -> dict[str, Any]:
    """Process a structured context escalation request from the LLM.

    Returns a result dict with keys:
      - approved: bool
      - reason: str (explanation)
      - fallback: str (if denied, "ask_user")
      - escalated_context: Any (if approved)
      - escalation_reason: str (if approved)
    """
    # --- Validate required fields ---
    if requested_type is None or reason is None:
        raise ValueError("context_request requires requested_type and reason")

    if requested_type not in CONTEXT_LEVELS:
        entry = {
            "purpose": purpose_id,
            "requested_type": requested_type,
            "reason": reason,
            "scope": scope,
            "approved": False,
            "denial_reason": "unknown_context_level",
        }
        EscalationLog.append(entry)
        return {"approved": False, "reason": "unknown context level", "fallback": "ask_user"}

    # --- Validate reason is non-empty ---
    if not isinstance(reason, str) or not reason.strip():
        entry = {
            "purpose": purpose_id,
            "requested_type": requested_type,
            "reason": reason,
            "scope": scope,
            "approved": False,
            "denial_reason": "empty_reason",
        }
        EscalationLog.append(entry)
        return {"approved": False, "reason": "reason must be non-empty", "fallback": "ask_user"}

    # --- Check scope ---
    scope_clean = (scope or "").strip().lower()
    if scope_clean in _BROAD_SCOPES:
        entry = {
            "purpose": purpose_id,
            "requested_type": requested_type,
            "reason": reason,
            "scope": scope,
            "approved": False,
            "denial_reason": "unscoped_broad_request",
        }
        EscalationLog.append(entry)
        return {
            "approved": False,
            "reason": "scope must be specific, not broad (e.g., 'failing_element', not 'entire_page')",
            "fallback": "ask_user",
        }

    # --- Check purpose max level ceiling ---
    max_allowed = PURPOSE_MAX_CONTEXT_LEVEL.get(purpose_id)
    if max_allowed is None:
        entry = {
            "purpose": purpose_id,
            "requested_type": requested_type,
            "reason": reason,
            "scope": scope,
            "approved": False,
            "denial_reason": "unknown_purpose",
        }
        EscalationLog.append(entry)
        return {"approved": False, "reason": "unknown purpose", "fallback": "ask_user"}

    if not is_within_ceiling(requested_type, max_allowed):
        entry = {
            "purpose": purpose_id,
            "requested_type": requested_type,
            "reason": reason,
            "scope": scope,
            "approved": False,
            "denial_reason": f"exceeds_max_level_{max_allowed}",
        }
        EscalationLog.append(entry)
        return {
            "approved": False,
            "reason": f"requested level {requested_type} exceeds max allowed {max_allowed} for purpose {purpose_id}",
            "fallback": "ask_user",
        }

    # --- Approved ---
    entry = {
        "purpose": purpose_id,
        "requested_type": requested_type,
        "reason": reason,
        "scope": scope,
        "approved": True,
        "escalation_reason": reason,
    }
    EscalationLog.append(entry)
    return {
        "approved": True,
        "escalated_context": f"<context_level={requested_type} scope={scope}>",
        "escalation_reason": reason,
    }
