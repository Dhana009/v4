"""
runtime/step_metadata.py

Pass 4b-2 — deterministic step kind classification + plan_ready annotator.

Step kind is metadata for frontend visibility (atomic / loop / section /
unknown). It does not change execution semantics. Backend owns runtime
truth; frontend must not infer kind without this payload.

Allowed values:
    atomic   — single action/assertion step (default).
    loop     — intent describes a repeated action over a collection
               ("each", "for each", "every", "all rows / cards / items").
    section  — step has 2+ child operations grouped under one heading.
    unknown  — malformed / missing step data.

Classification rules are conservative: when in doubt, the step is
atomic, not section/loop. Explicit backend-provided `step_kind` is
always preserved (never clobbered).
"""
from __future__ import annotations

import re
from typing import Any

_VALID_KINDS = frozenset({"atomic", "loop", "section", "unknown"})

# Intent patterns suggesting iteration over a collection.
# Conservative: only flag explicit iteration words. Plain "click X" stays atomic.
_LOOP_INTENT_PATTERN = re.compile(
    r"\b("
    r"each"
    r"|every"
    r"|forEach"
    r"|for\s+each"
    r"|all\s+(?:rows|cards|items|links|buttons|cells|tabs|panels|options)"
    r")\b",
    re.IGNORECASE,
)


def classify_step_kind(step: Any) -> str:
    """Return one of atomic / loop / section / unknown for a single step dict.

    Deterministic. No LLM, no DOM access.
    """
    if not isinstance(step, dict):
        return "unknown"

    children = step.get("children")
    if isinstance(children, list) and len(children) >= 2:
        return "section"

    intent_parts: list[str] = []
    for field in ("intent", "description", "text", "title", "label"):
        value = step.get(field)
        if isinstance(value, str) and value.strip():
            intent_parts.append(value)
    intent_text = " ".join(intent_parts)
    if intent_text and _LOOP_INTENT_PATTERN.search(intent_text):
        return "loop"

    # Has an intent / description / id-like presence: atomic.
    has_identity = any(
        step.get(field)
        for field in ("step_id", "id", "intent", "description", "text", "title")
    )
    if has_identity:
        return "atomic"

    return "unknown"


def _normalize_child_op(child: Any, fallback_index: int) -> dict[str, Any] | None:
    """Coerce one child entry into a stable frontend-facing shape.

    Returns None if the entry is not a dict (frontend must not see fake
    children). Stable fields: child_id, type, description, status, target.
    All optional except child_id.
    """
    if not isinstance(child, dict):
        return None
    out: dict[str, Any] = dict(child)
    cid_raw = (
        out.get("child_id")
        or out.get("operation_id")
        or out.get("id")
    )
    cid = str(cid_raw).strip() if cid_raw not in (None, "") else f"op_{fallback_index + 1}"
    out["child_id"] = cid
    return out


def normalize_plan_steps_children(payload: dict[str, Any]) -> dict[str, Any]:
    """Ensure every plan_ready step's `children` is a list of dicts with stable
    `child_id`. Non-list children become []; malformed entries are dropped.
    Frontend can iterate `step.children` without defensive checks.
    """
    if not isinstance(payload, dict):
        return payload
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return payload
    for step in steps:
        if not isinstance(step, dict):
            continue
        raw = step.get("children")
        if raw is None:
            continue  # leave alone; absence means atomic step
        if not isinstance(raw, list):
            step["children"] = []
            continue
        cleaned: list[dict[str, Any]] = []
        for i, c in enumerate(raw):
            norm = _normalize_child_op(c, i)
            if norm is not None:
                cleaned.append(norm)
        step["children"] = cleaned
    return payload


def annotate_plan_steps_with_kind(payload: dict[str, Any]) -> dict[str, Any]:
    """Walk plan_ready payload steps, attach `step_kind`.

    Preserves any explicit backend `step_kind` value if it is one of the
    allowed values. Invalid existing values are normalized to "unknown" so
    the frontend never reads a fake kind.
    """
    if not isinstance(payload, dict):
        return payload
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return payload
    for step in steps:
        if not isinstance(step, dict):
            continue
        existing = step.get("step_kind")
        if isinstance(existing, str) and existing in _VALID_KINDS:
            continue
        if existing is not None and existing not in _VALID_KINDS:
            # Invalid explicit value — normalize, don't trust.
            step["step_kind"] = "unknown"
            continue
        step["step_kind"] = classify_step_kind(step)
    return payload
