"""
runtime/memory_selection_policy.py

Memory selection policy: backend stores detailed memory but LLM receives
only a relevant per-purpose subset.

Source rule: Runtime Policy Spec — full chat history not sent by default.
Old plans/traces stored but not auto-included. Memory selection logged with reason.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# MemoryItem
# ---------------------------------------------------------------------------

@dataclass
class MemoryItem:
    category: str
    content: str
    tokens: int = 100


# ---------------------------------------------------------------------------
# Secret / sensitive categories (never selected)
# ---------------------------------------------------------------------------

_SECRET_CATEGORIES: frozenset[str] = frozenset({
    "credentials", "api_keys", "secrets", "passwords", "auth_tokens",
    "private_keys", "sensitive_data",
})

# Categories that hold old history (never auto-selected)
_HISTORY_CATEGORIES: frozenset[str] = frozenset({
    "chat_history", "old_plan", "archived_trace", "old_traces",
})

# Default 20000 token limit
_DEFAULT_MAX_TOKENS = 20_000


# ---------------------------------------------------------------------------
# Per-purpose memory selection defaults
# ---------------------------------------------------------------------------

MEMORY_SELECTION_DEFAULTS: dict[str, list[str]] = {
    "intent_classifier": ["user_message"],
    "clarification_generator": ["user_message", "field_name"],
    "page_intelligence_summarizer": ["user_message", "page_state"],
    "page_validation_recommender": ["user_message", "page_state", "page_intelligence"],
    "journey_planner": ["user_message", "page_state", "requirements"],
    "step_plan_normalizer": ["user_message", "current_plan", "page_state", "locator_context"],
    "plan_diff_editor": ["user_message", "current_plan", "page_state"],
    "locator_specialist": ["user_message", "locator_context", "page_state"],
    "custom_assertion_planner": ["user_message", "current_result", "original_step"],
    "execution_driver": ["user_message", "confirmed_operation"],
    "recovery_diagnoser": ["error_context", "recent_trace", "failure_evidence"],
    "replay_repair_specialist": ["original_trace", "replay_failure"],
    "user_response_writer": ["user_message"],
    "trace_summarizer": ["user_message", "recent_trace"],
}


# ---------------------------------------------------------------------------
# Selection log
# ---------------------------------------------------------------------------

_selection_log: list[dict[str, Any]] = []


def clear_selection_log() -> None:
    _selection_log.clear()


def get_selection_log() -> list[dict[str, Any]]:
    return list(_selection_log)


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------

def select_memory_for_purpose(
    purpose_id: str,
    all_memory: list[MemoryItem],
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> list[MemoryItem]:
    """Select relevant memory items for *purpose_id*.

    Filters by allowed categories, excludes secrets and history,
    and enforces *max_tokens* ceiling.
    """
    allowed_categories = MEMORY_SELECTION_DEFAULTS.get(purpose_id)
    if allowed_categories is None:
        raise ValueError(f"Unknown purpose_id: {purpose_id!r}")

    allowed_set = set(allowed_categories)

    # Filter: only allowed categories, never secrets, never old history
    filtered = [
        item for item in all_memory
        if item.category in allowed_set
        and item.category not in _SECRET_CATEGORIES
        and item.category not in _HISTORY_CATEGORIES
    ]

    # Enforce token ceiling
    selected: list[MemoryItem] = []
    total = 0
    for item in filtered:
        if total + item.tokens > max_tokens:
            break
        selected.append(item)
        total += item.tokens

    # Log selection
    _selection_log.append({
        "purpose": purpose_id,
        "selected_categories": [m.category for m in selected],
        "total_tokens": total,
        "max_tokens": max_tokens,
    })

    return selected
