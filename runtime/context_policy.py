"""
runtime/context_policy.py

Purpose-to-context-level defaults and context builders for L0–L5.

Source rule: Runtime Policy Spec — planning purposes default to L0–L2 (never L5).
Recovery purposes default to L4. Secrets always redacted. L5 capped at 50KB.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from typing import Any

from runtime.context_levels import (
    CONTEXT_LEVELS,
    LEVEL_ORDER,
    _SECRET_KEYS,
    level_rank,
)


# ---------------------------------------------------------------------------
# Purpose → default context level
# ---------------------------------------------------------------------------

PURPOSE_CONTEXT_DEFAULTS: dict[str, str] = {
    "intent_classifier": "L0",
    "clarification_generator": "L0",
    "page_intelligence_summarizer": "L1",
    "page_validation_recommender": "L3",
    "journey_planner": "L1",
    "step_plan_normalizer": "L1",
    "plan_diff_editor": "L2",
    "locator_specialist": "L2",
    "custom_assertion_planner": "L1",
    "execution_driver": "L0",
    "recovery_diagnoser": "L4",
    "replay_repair_specialist": "L4",
    "user_response_writer": "L0",
    "trace_summarizer": "L2",
}


def get_context_level_for_purpose(purpose_id: str, override: str | None = None) -> str:
    """Return the context level for *purpose_id*, or *override* if provided.

    Raises ValueError for unknown purposes.
    """
    if override is not None:
        if override not in CONTEXT_LEVELS:
            raise ValueError(f"Unknown context level override: {override!r}")
        return override
    level = PURPOSE_CONTEXT_DEFAULTS.get(purpose_id)
    if level is None:
        raise ValueError(f"Unknown purpose_id: {purpose_id!r}")
    return level


# ---------------------------------------------------------------------------
# Context builders per level
# ---------------------------------------------------------------------------

_L5_MAX_BYTES = CONTEXT_LEVELS["L5"]["max_dom_bytes"]


def _redact_secrets(d: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *d* without secret keys."""
    return {k: v for k, v in d.items() if k.lower() not in _SECRET_KEYS}


def _build_l0(page_state: dict[str, Any]) -> dict[str, Any]:
    """L0: user message + phase/modal_state only. No DOM, no element."""
    result: dict[str, Any] = {}
    for key in ("phase", "modal_state", "user_message"):
        if key in page_state:
            result[key] = page_state[key]
    return result


def _build_l1(page_state: dict[str, Any]) -> dict[str, Any]:
    """L1: L0 + element descriptor."""
    result = _build_l0(page_state)
    if "element" in page_state:
        result["element"] = page_state["element"]
    return result


def _build_l2(page_state: dict[str, Any]) -> dict[str, Any]:
    """L2: L1 + section summary."""
    result = _build_l1(page_state)
    if "section_summary" in page_state:
        result["section_summary"] = page_state["section_summary"]
    return result


def _build_l3(page_state: dict[str, Any]) -> dict[str, Any]:
    """L3: L2 + page intelligence (may be None if PI not yet live)."""
    result = _build_l2(page_state)
    result["page_intelligence"] = page_state.get("page_intelligence", None)
    return result


def _build_l4(page_state: dict[str, Any]) -> dict[str, Any]:
    """L4: focused debug packet — failure evidence, trace, error."""
    result: dict[str, Any] = {}
    for key in ("phase", "modal_state", "user_message"):
        if key in page_state:
            result[key] = page_state[key]
    for key in ("failure_evidence", "trace", "error", "locator_packet", "recovery_context"):
        if key in page_state:
            result[key] = page_state[key]
    return result


def _build_l5(page_state: dict[str, Any]) -> dict[str, Any]:
    """L5: capped raw DOM with secrets redacted."""
    # Start with redacted copy (removes secret keys)
    clean = _redact_secrets(page_state)
    # Cap raw_dom at 50KB
    if "raw_dom" in clean:
        dom = clean["raw_dom"]
        if isinstance(dom, str) and len(dom.encode("utf-8")) > _L5_MAX_BYTES:
            clean["raw_dom"] = dom.encode("utf-8")[:_L5_MAX_BYTES].decode("utf-8", errors="replace")
    # Remove explicit secret/password fields that slipped through
    for key in list(clean.keys()):
        if key.lower() in _SECRET_KEYS:
            del clean[key]
    return clean


_BUILDERS = {
    "L0": _build_l0,
    "L1": _build_l1,
    "L2": _build_l2,
    "L3": _build_l3,
    "L4": _build_l4,
    "L5": _build_l5,
}


def build_context_for_level(level: str, *, page_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a context dict appropriate for *level*.

    page_state is the raw runtime state; the builder will strip/include
    fields according to the level ceiling.
    """
    if level not in CONTEXT_LEVELS:
        raise ValueError(f"Unknown context level: {level!r}")
    if page_state is None:
        page_state = {}
    builder = _BUILDERS[level]
    return builder(page_state)
