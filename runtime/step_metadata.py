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


# ---------------------------------------------------------------------------
# Blocked-step metadata (Pass 4b-4)
# ---------------------------------------------------------------------------

_VALID_BLOCKED_REASONS = frozenset(
    {"missing_data", "wrong_page", "locator_unstable", "permission_required", "unknown"}
)

# Accepted aliases for legacy/runtime synonyms.
_BLOCKED_REASON_ALIASES = {
    "weak_locator": "locator_unstable",
}


def _normalize_blocked_object(raw: Any) -> dict[str, Any] | None:
    """Coerce a `step.blocked` value into a stable frontend-facing shape.

    Returns None when input is not a dict (frontend must never see a fake
    blocked state). When dict but missing/invalid `reason`, reason is set
    to "unknown" so a blocked step never silently appears unblocked.
    """
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = dict(raw)
    reason = out.get("reason")
    if isinstance(reason, str):
        reason = _BLOCKED_REASON_ALIASES.get(reason, reason)
        if reason not in _VALID_BLOCKED_REASONS:
            reason = "unknown"
    else:
        reason = "unknown"
    out["reason"] = reason

    refs = out.get("refs")
    if isinstance(refs, list):
        cleaned_refs: list[Any] = []
        for r in refs:
            if isinstance(r, (str, int)):
                s = str(r).strip()
                if s:
                    cleaned_refs.append(s)
            elif isinstance(r, dict):
                cleaned_refs.append(r)
        out["refs"] = cleaned_refs
    else:
        out["refs"] = []

    if "message" in out and not isinstance(out["message"], str):
        out["message"] = ""
    if "action_label" in out and not isinstance(out["action_label"], str):
        out["action_label"] = ""
    return out


def normalize_plan_steps_blocked(payload: dict[str, Any]) -> dict[str, Any]:
    """Walk plan_ready payload steps, normalize `step.blocked`.

    - Missing `blocked` key: left untouched (step is not blocked).
    - Non-dict `blocked` value: dropped (set to None and removed) so the
      frontend never reads a malformed blocked state as truth.
    - Valid blocked dict: reason validated against the allowed set,
      refs cleaned to a list of strings / dicts.
    """
    if not isinstance(payload, dict):
        return payload
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return payload
    for step in steps:
        if not isinstance(step, dict):
            continue
        if "blocked" not in step:
            continue
        normalized = _normalize_blocked_object(step["blocked"])
        if normalized is None:
            del step["blocked"]
        else:
            step["blocked"] = normalized
    return payload


# ---------------------------------------------------------------------------
# Precondition metadata (Pass 4b-5)
# ---------------------------------------------------------------------------

_VALID_PRECONDITION_STATUS = frozenset({"passed", "failed", "unknown"})


def _normalize_precondition_object(raw: Any) -> dict[str, Any] | None:
    """Coerce a `step.precondition` value into a stable frontend-facing shape.

    Returns None when input is not a dict. Status validated against the
    allowed set; missing/invalid → "unknown" so the frontend never reads
    a fake "passed" or "failed".
    """
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = dict(raw)
    status = out.get("status")
    if not (isinstance(status, str) and status in _VALID_PRECONDITION_STATUS):
        status = "unknown"
    out["status"] = status

    for field in ("expected_url", "current_url", "message"):
        val = out.get(field)
        if val is None:
            continue
        if not isinstance(val, str):
            out[field] = ""
        else:
            out[field] = val
    return out


def normalize_plan_steps_precondition(payload: dict[str, Any]) -> dict[str, Any]:
    """Walk plan_ready payload steps, normalize `step.precondition`.

    - Missing key: untouched.
    - Non-dict value: key removed entirely.
    - Valid dict: status validated; URL/message fields kept as strings.
    """
    if not isinstance(payload, dict):
        return payload
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return payload
    for step in steps:
        if not isinstance(step, dict):
            continue
        if "precondition" not in step:
            continue
        normalized = _normalize_precondition_object(step["precondition"])
        if normalized is None:
            del step["precondition"]
        else:
            step["precondition"] = normalized
    return payload


# ---------------------------------------------------------------------------
# Child operation count (Pass 4b-6)
# ---------------------------------------------------------------------------

def normalize_plan_steps_child_count(payload: dict[str, Any]) -> dict[str, Any]:
    """Walk plan_ready payload steps, normalize `step.child_op_count`.

    Order of precedence:
      1. Explicit non-negative int from backend → preserved.
      2. Explicit invalid value (non-int, negative, etc.) → derived from
         len(children) if children is a list, else removed.
      3. Missing key + children list present → set to len(children).
      4. Missing key + no children → key not invented (left absent).

    Must run AFTER normalize_plan_steps_children so children is already a
    clean list.
    """
    if not isinstance(payload, dict):
        return payload
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return payload
    for step in steps:
        if not isinstance(step, dict):
            continue
        children = step.get("children")
        children_len = len(children) if isinstance(children, list) else None

        explicit = step.get("child_op_count")
        explicit_valid = (
            isinstance(explicit, int)
            and not isinstance(explicit, bool)
            and explicit >= 0
        )

        if explicit_valid:
            continue
        if explicit is not None:
            # Invalid explicit value present.
            if children_len is not None:
                step["child_op_count"] = children_len
            else:
                del step["child_op_count"]
            continue
        if children_len is not None:
            step["child_op_count"] = children_len


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
