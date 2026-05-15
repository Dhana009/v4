"""
runtime/plan_edit_classifier.py

Plan-edit intent classifier for Complete LLM Mode.

Source rule: P0 Scenarios Spec §5.2 (L462–476) — classify plan-edit requests
into one of the 11 finite plan-edit categories before mutating the plan.

No LLM calls. No I/O. Deterministic keyword heuristics only.
When confidence < 0.5, callers should escalate to controller.call(purpose=...).

Controller integration (runtime_policy §15):
  Wrap with controller.call(purpose="plan_edit_classifier", deterministic_safe=True)
  when telemetry is needed.  LLM escalation path lands in a separate wire-in slice.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Public enum tuple — taken verbatim from spec §5.2 (L464–476) + "unknown"
# for the no-match fallback.
# ---------------------------------------------------------------------------
PLAN_EDIT_LABELS: tuple[str, ...] = (
    "discuss_only",
    "add_operation",
    "remove_operation",
    "reorder_operations",
    "replace_target",
    "change_expected_outcome",
    "split_step",
    "merge_steps",
    "skip_step",
    "apply_revision",
    "reject_revision",
    "unknown",
)

# ---------------------------------------------------------------------------
# Keyword signals (order = priority; first match wins)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    # reject_revision — must come before apply_revision
    (("reject", "undo revision", "revert revision", "discard revision", "cancel revision",
      "don't apply", "do not apply", "rollback"), "reject_revision"),

    # apply_revision
    (("apply revision", "apply the revision", "apply that", "confirm revision",
      "accept revision", "go ahead with revision", "apply changes"), "apply_revision"),

    # discuss_only — "just talk", "what if", "what would", "should we"
    (("what if", "what would", "should we", "would it", "discuss", "thinking about",
      "consider", "explore", "let's talk", "just curious"), "discuss_only"),

    # skip_step
    (("skip", "ignore step", "skip step", "pass this step", "omit step",
      "leave out"), "skip_step"),

    # merge_steps
    (("merge", "combine steps", "combine these", "join steps", "consolidate"), "merge_steps"),

    # split_step
    (("split", "break into", "divide step", "separate step", "break step"), "split_step"),

    # reorder_operations
    (("reorder", "move step", "rearrange", "swap steps", "change order",
      "before step", "after step", "move before", "move after"), "reorder_operations"),

    # remove_operation
    (("remove step", "remove operation", "delete step", "drop step", "take out step",
      "eliminate step", "get rid of step", "remove the step"), "remove_operation"),

    # add_operation
    (("add step", "add operation", "insert step", "new step", "include step",
      "append step", "add a step"), "add_operation"),

    # replace_target
    (("replace locator", "change locator", "use different locator", "replace selector",
      "change selector", "replace target", "different element", "update locator",
      "change element"), "replace_target"),

    # change_expected_outcome
    (("change assertion", "change expected", "update assertion", "different outcome",
      "expected result", "change the outcome", "update expected", "modify assertion",
      "change what we expect"), "change_expected_outcome"),
]

# ---------------------------------------------------------------------------
# Confidence weights
# ---------------------------------------------------------------------------

_HIGH_CONFIDENCE = 0.85
_MED_CONFIDENCE = 0.65
_LOW_CONFIDENCE = 0.40


def _score_text(text_lower: str, keywords: tuple[str, ...]) -> int:
    """Return count of keyword hits in text."""
    return sum(1 for kw in keywords if kw in text_lower)


def classify(text: str, ctx: dict | None = None) -> dict:  # noqa: ARG001
    """Classify a plan-edit request.

    Parameters
    ----------
    text:
        Raw user message or plan-edit instruction.
    ctx:
        Optional context dict (unused by heuristics; reserved for LLM escalation).

    Returns
    -------
    dict with keys:
        label      — one of PLAN_EDIT_LABELS
        confidence — float in [0.0, 1.0]
        reasons    — list[str] explaining the match
    """
    if not text or not text.strip():
        return {"label": "unknown", "confidence": 0.0, "reasons": ["empty input"]}

    text_lower = text.lower().strip()
    best_label: str = "unknown"
    best_hits: int = 0
    best_keywords: tuple[str, ...] = ()

    for keywords, label in _PATTERNS:
        hits = _score_text(text_lower, keywords)
        if hits > best_hits:
            best_hits = hits
            best_label = label
            best_keywords = keywords

    if best_hits == 0:
        return {"label": "unknown", "confidence": 0.0, "reasons": ["no keyword match"]}

    matched = [kw for kw in best_keywords if kw in text_lower]

    # Confidence tiers based on hit density relative to available keywords
    ratio = best_hits / max(len(best_keywords), 1)
    if ratio >= 0.3 or best_hits >= 3:
        confidence = _HIGH_CONFIDENCE
    elif best_hits >= 2:
        confidence = _MED_CONFIDENCE
    else:
        confidence = _LOW_CONFIDENCE

    return {
        "label": best_label,
        "confidence": confidence,
        "reasons": [f"matched keyword(s): {matched}"],
    }
