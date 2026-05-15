"""
runtime/schema_validation_policy.py

Schema validation and retry/fail-closed policy for all LLM runtime purposes.

Source rule: Runtime Policy Spec — every purpose has schema.
Schema failure retries once, then fails closed. Prose cannot silently continue.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# SchemaValidationResult
# ---------------------------------------------------------------------------

@dataclass
class SchemaValidationResult:
    valid: bool
    retried: bool = False
    fallback: str | None = None
    output: Any = None
    error: str | None = None
    retry_count: int = 0


# ---------------------------------------------------------------------------
# Per-purpose fallback policy on schema failure
# ---------------------------------------------------------------------------

PURPOSE_SCHEMA_FALLBACK: dict[str, str] = {
    "intent_classifier": "ask_user",
    "clarification_generator": "ask_user",
    "page_intelligence_summarizer": "fail_closed",
    "page_validation_recommender": "ask_user",
    "journey_planner": "ask_user",
    "step_plan_normalizer": "ask_user",
    "plan_diff_editor": "ask_user",
    "locator_specialist": "ask_user",
    "custom_assertion_planner": "ask_user",
    "execution_driver": "fail_closed",
    "recovery_diagnoser": "fail_closed",
    "replay_repair_specialist": "fail_closed",
    "user_response_writer": "ask_user",
    "trace_summarizer": "fail_closed",
}


def get_fallback_for_purpose(purpose_id: str) -> str:
    """Return the fallback policy on schema failure for *purpose_id*."""
    fallback = PURPOSE_SCHEMA_FALLBACK.get(purpose_id)
    if fallback is None:
        # Check the policy registry
        try:
            from runtime.llm_policy_registry import POLICY_REGISTRY
            policy = POLICY_REGISTRY.get(purpose_id)
            return policy.get("fallback_policy", "fail_closed")
        except (ValueError, KeyError):
            return "fail_closed"
    return fallback


# ---------------------------------------------------------------------------
# Validation log
# ---------------------------------------------------------------------------

_validation_log: list[dict[str, Any]] = []


def clear_validation_log() -> None:
    _validation_log.clear()


def get_validation_log() -> list[dict[str, Any]]:
    return list(_validation_log)


# ---------------------------------------------------------------------------
# Output validator
# ---------------------------------------------------------------------------

def _is_structured(output: str) -> bool:
    """Return True if *output* appears to be structured (JSON-parseable)."""
    if not isinstance(output, str):
        return False
    stripped = output.strip()
    if not stripped:
        return False
    # Must start with JSON object or array
    if stripped[0] not in ('{', '['):
        return False
    try:
        json.loads(stripped)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def validate_output(
    purpose_id: str,
    output: str,
    retry_fn: Callable[[str, str], str] | None = None,
) -> SchemaValidationResult:
    """Validate LLM output for *purpose_id*.

    1. If valid → return valid result.
    2. If invalid and retry_fn provided → retry once.
    3. If retry valid → return valid (retried=True).
    4. If retry invalid or no retry_fn → apply fallback policy.

    All outcomes are logged.
    """
    retry_count = 0

    # First validation attempt
    if _is_structured(output):
        result = SchemaValidationResult(valid=True, output=output, retry_count=0)
        _validation_log.append({
            "purpose": purpose_id,
            "valid": True,
            "retried": False,
            "retry_count": 0,
            "fallback": None,
        })
        return result

    # First attempt failed — retry if retry_fn provided
    retry_count = 1
    if retry_fn is not None:
        retry_output = retry_fn(purpose_id, output)
        if _is_structured(retry_output):
            result = SchemaValidationResult(
                valid=True,
                retried=True,
                output=retry_output,
                retry_count=1,
            )
            _validation_log.append({
                "purpose": purpose_id,
                "valid": True,
                "retried": True,
                "retry_count": 1,
                "fallback": None,
            })
            return result

    # Both attempts failed (or no retry_fn)
    fallback = get_fallback_for_purpose(purpose_id)
    result = SchemaValidationResult(
        valid=False,
        retried=(retry_fn is not None),
        fallback=fallback,
        error="schema_failure",
        retry_count=retry_count,
    )
    _validation_log.append({
        "purpose": purpose_id,
        "valid": False,
        "retried": (retry_fn is not None),
        "retry_count": retry_count,
        "fallback": fallback,
        "error": "schema_failure",
    })
    return result
