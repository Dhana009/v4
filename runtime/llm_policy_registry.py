"""
runtime/llm_policy_registry.py

Single typed registry containing all 14 LLM runtime purpose policies.

Source rule: Runtime Policy Spec — every LLM call must declare a purpose_id.
Unknown purpose fails closed immediately (raises ValueError — no fallback call).
Every purpose has complete metadata: model_class, context_policy, skill_policy,
tool_policy, schema_id, validator_id, fallback_policy, retry_policy, telemetry_fields.

Modularization rule: policy logic goes in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from typing import Any

from runtime.llm_purpose_policy import (
    ALLOWED_FALLBACK_POLICIES,
    ALLOWED_MODEL_CLASSES,
    LLMPurposePolicy,
    REQUIRED_PURPOSE_IDS,
)
from runtime.tool_schema_policy import planning_tools_for_purpose


# ---------------------------------------------------------------------------
# Policy builder helpers
# ---------------------------------------------------------------------------

def _context_policy(purpose: str, *, context_level: str = "compact") -> dict[str, Any]:
    return {
        "purpose": purpose,
        "context_level": context_level,
        "context_mode": "compact",
        "allow_full_dom": False,
        "allow_full_history": False,
        "allow_raw_dom": False,
        "allow_unbounded_context": False,
    }


def _skill_policy(purpose: str, *, skill_names: tuple[str, ...], token_budget: int) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "skill_level": "core_compact",
        "load_all": False,
        "required_core_skills": ["llm_runtime_controller"],
        "purpose_skills": list(skill_names),
        "skill_budget": token_budget,
        "skill_scope": "purpose_specific",
    }


def _tool_policy(
    purpose: str,
    *,
    planning_tools: tuple[str, ...],
    executing_tools: tuple[str, ...] = (),
    recovery_tools: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "allowed_tools_by_phase": {
            "planning": list(planning_tools),
            "plan_review": list(planning_tools),
            "awaiting_confirmation": list(planning_tools),
            "executing": list(executing_tools),
            "recovery": list(recovery_tools),
            "completed": [],
        },
        "deny_reason": "deny_by_default",
        "default_deny_reason": "deny_by_default",
        "phase_policy": "deny_by_default",
    }


def _retry_policy(purpose: str, *, schema_retry_limit: int = 1) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "schema_retry_limit": schema_retry_limit,
        "retry_limit": schema_retry_limit,
        "fallback_action": "fail_closed",
        "fallback": "fail_closed",
        "on_failure": "fail_closed",
    }


_DEFAULT_TELEMETRY_FIELDS: dict[str, str] = {
    "purpose": "str",
    "model": "str",
    "call_id": "str",
    "skill_count": "int",
    "skills_loaded": "list[str]",
    "tool_count": "int",
    "tools_exposed_count": "int",
    "context_mode": "str",
    "context_level": "str",
    "token_budget": "int",
    "estimated_input_tokens": "int",
    "estimated_output_tokens": "int|None",
    "retry_count": "int",
    "validation_status": "str",
    "latency_ms": "int",
    "schema_id": "str",
    "schema_version": "int",
    "error_code": "str|None",
}


def _telemetry_fields(purpose: str) -> dict[str, str]:
    fields = dict(_DEFAULT_TELEMETRY_FIELDS)
    fields["purpose"] = purpose
    return fields


def _build_policy(
    *,
    purpose: str,
    model_class: str,
    skill_names: tuple[str, ...],
    token_budget: int,
    executing_tools: tuple[str, ...] = (),
    recovery_tools: tuple[str, ...] = (),
    fallback_policy: str = "fail_closed",
    context_level: str = "compact",
) -> LLMPurposePolicy:
    assert model_class in ALLOWED_MODEL_CLASSES, f"Bad model_class {model_class!r}"
    assert fallback_policy in ALLOWED_FALLBACK_POLICIES, f"Bad fallback {fallback_policy!r}"
    planning_tools = planning_tools_for_purpose(purpose)
    return LLMPurposePolicy(
        purpose_id=purpose,
        model_class=model_class,
        context_policy=_context_policy(purpose, context_level=context_level),
        skill_policy=_skill_policy(purpose, skill_names=skill_names, token_budget=token_budget),
        tool_policy=_tool_policy(
            purpose,
            planning_tools=planning_tools,
            executing_tools=executing_tools,
            recovery_tools=recovery_tools,
        ),
        schema_id=f"{purpose}.v1",
        validator_id="schema_validator",
        fallback_policy=fallback_policy,
        retry_policy=_retry_policy(purpose),
        telemetry_fields=_telemetry_fields(purpose),
    )


# ---------------------------------------------------------------------------
# Skill name constants
# ---------------------------------------------------------------------------

_PERSONA = ("prompt_persona_skill_loading",)
_LOCATOR = ("locator_strategy",)
_MIXED = ("prompt_persona_skill_loading", "locator_strategy")


# ---------------------------------------------------------------------------
# LLMPolicyRegistry
# ---------------------------------------------------------------------------

class LLMPolicyRegistry:
    """Registry mapping purpose_id → typed policy dict.

    Unknown purpose raises ValueError immediately (fail-closed).
    get() always returns a safe copy — mutating the return value
    cannot corrupt the registry.
    """

    def __init__(self, policies: dict[str, LLMPurposePolicy]) -> None:
        missing = set(REQUIRED_PURPOSE_IDS) - policies.keys()
        if missing:
            raise ValueError(f"Registry is missing required purposes: {sorted(missing)}")
        self._policies: dict[str, LLMPurposePolicy] = dict(policies)

    def get(self, purpose: str | None) -> dict[str, Any]:
        """Return a safe copy of the policy for *purpose*.

        Raises ValueError for unknown / empty / None purposes.
        """
        if not purpose or not isinstance(purpose, str):
            raise ValueError(f"Unknown LLM purpose: {purpose!r}")
        normalized = str(purpose).strip()
        if normalized not in self._policies:
            raise ValueError(f"Unknown LLM purpose: {normalized!r}")
        # Return a deep-enough copy so callers cannot corrupt internal state.
        policy = self._policies[normalized]
        return dict(policy)

    def list_purposes(self) -> list[str]:
        return list(self._policies.keys())

    def __contains__(self, purpose: object) -> bool:
        if not isinstance(purpose, str):
            return False
        return str(purpose).strip() in self._policies


# ---------------------------------------------------------------------------
# Default registry factory
# ---------------------------------------------------------------------------

def build_default_registry() -> LLMPolicyRegistry:
    """Build and return a fresh LLMPolicyRegistry with all 17 purposes."""
    policies: dict[str, LLMPurposePolicy] = {
        "intent_classifier": _build_policy(
            purpose="intent_classifier",
            model_class="cheap",
            skill_names=_PERSONA,
            token_budget=1000,
        ),
        "clarification_generator": _build_policy(
            purpose="clarification_generator",
            model_class="cheap",
            skill_names=_PERSONA,
            token_budget=1000,
        ),
        "page_intelligence_summarizer": _build_policy(
            purpose="page_intelligence_summarizer",
            model_class="cheap",
            skill_names=_LOCATOR,
            token_budget=1400,
        ),
        "page_validation_recommender": _build_policy(
            purpose="page_validation_recommender",
            model_class="main",
            skill_names=_LOCATOR,
            token_budget=1800,
        ),
        "journey_planner": _build_policy(
            purpose="journey_planner",
            model_class="main",
            skill_names=_PERSONA,
            token_budget=2400,
        ),
        "step_plan_normalizer": _build_policy(
            purpose="step_plan_normalizer",
            model_class="main",
            skill_names=_PERSONA,
            token_budget=3000,
        ),
        "plan_diff_editor": _build_policy(
            purpose="plan_diff_editor",
            model_class="main",
            skill_names=_PERSONA,
            token_budget=2200,
        ),
        "locator_specialist": _build_policy(
            purpose="locator_specialist",
            model_class="main",
            skill_names=_LOCATOR,
            token_budget=2200,
        ),
        "custom_assertion_planner": _build_policy(
            purpose="custom_assertion_planner",
            model_class="main",
            skill_names=_MIXED,
            token_budget=2200,
        ),
        "execution_driver": _build_policy(
            purpose="execution_driver",
            model_class="main",
            skill_names=_PERSONA,
            token_budget=1800,
            executing_tools=("action_assert", "action_click", "action_fill"),
        ),
        "recovery_diagnoser": _build_policy(
            purpose="recovery_diagnoser",
            model_class="main",
            skill_names=_PERSONA,
            token_budget=1800,
            recovery_tools=("browser_get_state", "ask_user"),
        ),
        "replay_repair_specialist": _build_policy(
            purpose="replay_repair_specialist",
            model_class="main",
            skill_names=_PERSONA,
            token_budget=1800,
            recovery_tools=("browser_get_state", "ask_user"),
        ),
        "user_response_writer": _build_policy(
            purpose="user_response_writer",
            model_class="cheap",
            skill_names=_PERSONA,
            token_budget=1000,
        ),
        "trace_summarizer": _build_policy(
            purpose="trace_summarizer",
            model_class="cheap",
            skill_names=_PERSONA,
            token_budget=1000,
        ),
        # --- classifier routing purposes (runtime_policy §15) ---
        # Deterministic classifiers routed through controller so any future
        # LLM escalation path gets schema-retry + _validate_response.
        "journey_classifier": _build_policy(
            purpose="journey_classifier",
            model_class="cheap",
            skill_names=_PERSONA,
            token_budget=800,
        ),
        "failure_classifier": _build_policy(
            purpose="failure_classifier",
            model_class="cheap",
            skill_names=_PERSONA,
            token_budget=800,
        ),
        # --- agent_fallback purpose (runtime_policy §15) ---
        # Closes the direct model_router.call() bypass in agent.py.
        # TODO(follow-up): retire once all agent paths have dedicated purposes.
        "agent_fallback": _build_policy(
            purpose="agent_fallback",
            model_class="main",
            skill_names=_PERSONA,
            token_budget=3200,
        ),
    }
    return LLMPolicyRegistry(policies)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

POLICY_REGISTRY: LLMPolicyRegistry = build_default_registry()
