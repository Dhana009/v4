"""
multi_agent_orchestrator.py

Stateless orchestrator that maps named agent roles (PRD 07 + 06 multi-model track)
to existing LLMRuntimeController.call(purpose=...) calls.

No wire-in to agent.py in this slice — pure addition.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

if TYPE_CHECKING:
    from runtime.llm_runtime_controller import LLMRuntimeController


# ---------------------------------------------------------------------------
# Role enum
# ---------------------------------------------------------------------------

class AgentRole(str, Enum):
    MAIN_ORCHESTRATOR = "main_orchestrator"
    PAGE_INTELLIGENCE = "page_intelligence"
    STEP_RUNNER       = "step_runner"
    DEBUG_AGENT       = "debug_agent"
    CODEGEN_REVIEWER  = "codegen_reviewer"
    JUDGE_RISK        = "judge_risk"


# ---------------------------------------------------------------------------
# Invocation dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentInvocation:
    role:           AgentRole
    purpose:        str
    context:        dict
    tools:          tuple[str, ...] = field(default_factory=tuple)
    parent_run_id:  str | None = None
    parent_step_id: str | None = None


# ---------------------------------------------------------------------------
# Purpose → Role mapping table
# ---------------------------------------------------------------------------

# Keys are exact purpose strings used by LLMRuntimeController.call(purpose=...).
# Values are the AgentRole they map to.
_PURPOSE_TO_ROLE: dict[str, AgentRole] = {
    # Main Orchestrator purposes
    "journey_planner":              AgentRole.MAIN_ORCHESTRATOR,
    "agent_fallback":               AgentRole.MAIN_ORCHESTRATOR,
    "journey_classifier":           AgentRole.MAIN_ORCHESTRATOR,
    "step_classifier":              AgentRole.MAIN_ORCHESTRATOR,
    "plan_edit_classifier":         AgentRole.MAIN_ORCHESTRATOR,
    "permission_classifier":        AgentRole.MAIN_ORCHESTRATOR,
    "capability_classifier":        AgentRole.MAIN_ORCHESTRATOR,

    # Page Intelligence purposes
    "page_intelligence":            AgentRole.PAGE_INTELLIGENCE,
    "page_extraction":              AgentRole.PAGE_INTELLIGENCE,
    "page_validation_recommender":  AgentRole.PAGE_INTELLIGENCE,
    "locator_intelligence":         AgentRole.PAGE_INTELLIGENCE,
    "locator_issue_classifier":     AgentRole.PAGE_INTELLIGENCE,

    # Step Runner purposes
    "step_runner":                  AgentRole.STEP_RUNNER,
    "section_action_planner":       AgentRole.STEP_RUNNER,
    "deterministic_fast_path":      AgentRole.STEP_RUNNER,

    # Debug Agent purposes
    "failure_classifier":           AgentRole.DEBUG_AGENT,
    "debug_agent":                  AgentRole.DEBUG_AGENT,
    "debug_failure":                AgentRole.DEBUG_AGENT,
    "debug_locator":                AgentRole.DEBUG_AGENT,
    "debug_recovery":               AgentRole.DEBUG_AGENT,
    "recovery_manager":             AgentRole.DEBUG_AGENT,

    # Codegen Reviewer purposes
    "codegen_reviewer":             AgentRole.CODEGEN_REVIEWER,
    "replay_repair_specialist":     AgentRole.CODEGEN_REVIEWER,
    "plan_revision":                AgentRole.CODEGEN_REVIEWER,

    # Judge / Risk purposes
    "judge_risk":                   AgentRole.JUDGE_RISK,
    "risk_assessor":                AgentRole.JUDGE_RISK,
}

# Prefix rules applied when no exact match exists (longest-prefix wins).
_PURPOSE_PREFIX_TO_ROLE: list[tuple[str, AgentRole]] = [
    ("debug_",        AgentRole.DEBUG_AGENT),
    ("page_",         AgentRole.PAGE_INTELLIGENCE),
    ("locator_",      AgentRole.PAGE_INTELLIGENCE),
    ("replay_",       AgentRole.CODEGEN_REVIEWER),
    ("codegen_",      AgentRole.CODEGEN_REVIEWER),
    ("journey_",      AgentRole.MAIN_ORCHESTRATOR),
    ("step_",         AgentRole.STEP_RUNNER),
    ("judge_",        AgentRole.JUDGE_RISK),
    ("risk_",         AgentRole.JUDGE_RISK),
]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class MultiAgentOrchestrator:
    """
    Stateless (per-call) orchestrator that routes to named agent roles
    via LLMRuntimeController.call(purpose=...).

    The active-invocation registry is protected by an asyncio.Lock so it
    is safe to share a single orchestrator instance across concurrent tasks.
    """

    def __init__(self, controller: "LLMRuntimeController") -> None:
        self._controller = controller
        self._active: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def role_for_purpose(self, purpose: str) -> AgentRole:
        """Map a purpose string to an AgentRole.

        Lookup order:
        1. Exact match in _PURPOSE_TO_ROLE.
        2. Longest-prefix match in _PURPOSE_PREFIX_TO_ROLE.
        3. Default: MAIN_ORCHESTRATOR.
        """
        if purpose in _PURPOSE_TO_ROLE:
            return _PURPOSE_TO_ROLE[purpose]

        # Longest prefix wins
        matched_role: AgentRole | None = None
        matched_len = 0
        for prefix, role in _PURPOSE_PREFIX_TO_ROLE:
            if purpose.startswith(prefix) and len(prefix) > matched_len:
                matched_role = role
                matched_len = len(prefix)

        return matched_role if matched_role is not None else AgentRole.MAIN_ORCHESTRATOR

    async def invoke(self, inv: AgentInvocation) -> dict:
        """Execute an AgentInvocation via the underlying controller.

        Returns a dict:
            {
                "agent_invocation_id": str,
                "role":                str (AgentRole value),
                "purpose":             str,
                "parent_run_id":       str | None,
                "parent_step_id":      str | None,
                "response":            dict,
            }
        """
        agent_invocation_id = f"{inv.role.value}-{uuid4().hex[:12]}"

        envelope: dict = {
            "agent_invocation_id": agent_invocation_id,
            "role":                inv.role.value,
            "purpose":             inv.purpose,
            "parent_run_id":       inv.parent_run_id,
            "parent_step_id":      inv.parent_step_id,
            "response":            {},
        }

        # Register as in-flight
        async with self._lock:
            self._active[agent_invocation_id] = envelope.copy()

        try:
            response = await self._controller.call(
                purpose=inv.purpose,
                context=inv.context,
                tools=inv.tools,
                parent_run_id=inv.parent_run_id,
                parent_step_id=inv.parent_step_id,
            )
            envelope["response"] = response if isinstance(response, dict) else {"result": response}
        finally:
            async with self._lock:
                self._active.pop(agent_invocation_id, None)

        return envelope

    def list_active_invocations(self) -> list[dict]:
        """Return a snapshot of currently in-flight invocations."""
        # Safe read — dict copy is atomic enough for a snapshot; no lock needed.
        return list(self._active.values())


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def build_agent_status_event(
    invocation: dict,
    status: Literal["started", "completed", "failed"],
    error: str | None = None,
) -> dict:
    """Build a structured payload for the frontend *agent_status* subscription.

    Returns:
        {
            "type": "agent_status",
            "payload": {
                "agent_invocation_id": str,
                "role":                str,
                "purpose":             str,
                "parent_run_id":       str | None,
                "parent_step_id":      str | None,
                "status":              "started" | "completed" | "failed",
                "error":               str | None,
            }
        }
    """
    return {
        "type": "agent_status",
        "payload": {
            "agent_invocation_id": invocation.get("agent_invocation_id"),
            "role":                invocation.get("role"),
            "purpose":             invocation.get("purpose"),
            "parent_run_id":       invocation.get("parent_run_id"),
            "parent_step_id":      invocation.get("parent_step_id"),
            "status":              status,
            "error":               error,
        },
    }
