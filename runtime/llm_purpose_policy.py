"""
runtime/llm_purpose_policy.py

Typed purpose policy metadata for all 14 LLM runtime purposes.

Source rule: Runtime Policy Spec — every LLM call must declare a purpose_id.
Unknown purpose fails closed (no fallback LLM call).
Every purpose must have complete metadata:
  purpose_id, model_class, context_policy, skill_policy, tool_policy,
  schema_id, validator_id, fallback_policy, retry_policy, telemetry_fields.

Modularization rule: policy logic goes in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Canonical list of all allowed LLM runtime purposes
# ---------------------------------------------------------------------------

REQUIRED_PURPOSE_IDS: tuple[str, ...] = (
    "intent_classifier",
    "clarification_generator",
    "page_intelligence_summarizer",
    "page_validation_recommender",
    "journey_planner",
    "step_plan_normalizer",
    "plan_diff_editor",
    "locator_specialist",
    "custom_assertion_planner",
    "execution_driver",
    "recovery_diagnoser",
    "replay_repair_specialist",
    "user_response_writer",
    "trace_summarizer",
)

ALLOWED_MODEL_CLASSES: frozenset[str] = frozenset({"cheap", "main", "debug"})
ALLOWED_FALLBACK_POLICIES: frozenset[str] = frozenset({"ask_user", "fail_closed", "retry"})


# ---------------------------------------------------------------------------
# TypedDict for purpose policy
# ---------------------------------------------------------------------------

class LLMPurposePolicy(TypedDict):
    """Complete typed metadata for a single LLM runtime purpose."""

    purpose_id: str
    model_class: str           # "cheap" | "main" | "debug"
    context_policy: dict[str, Any]
    skill_policy: dict[str, Any]
    tool_policy: dict[str, Any]
    schema_id: str
    validator_id: str
    fallback_policy: str       # "ask_user" | "fail_closed" | "retry"
    retry_policy: dict[str, Any]
    telemetry_fields: dict[str, str]


# ---------------------------------------------------------------------------
# Module-level registry reference (populated by llm_policy_registry)
# ---------------------------------------------------------------------------

_REGISTRY: Any = None  # set by llm_policy_registry on import


def _get_registry() -> Any:
    global _REGISTRY  # noqa: PLW0603
    if _REGISTRY is None:
        from runtime.llm_policy_registry import POLICY_REGISTRY  # noqa: PLC0415
        _REGISTRY = POLICY_REGISTRY
    return _REGISTRY


def get_purpose_policy(purpose: str) -> dict[str, Any]:
    """Return a safe copy of the policy for *purpose*.

    Raises ValueError if the purpose is unknown.
    """
    return _get_registry().get(purpose)


def list_purposes() -> list[str]:
    """Return the sorted list of all known purpose IDs."""
    return _get_registry().list_purposes()


def is_known_purpose(purpose: str) -> bool:
    """Return True if *purpose* is a registered LLM runtime purpose."""
    if not purpose or not isinstance(purpose, str):
        return False
    return str(purpose).strip() in REQUIRED_PURPOSE_IDS
