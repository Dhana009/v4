"""
runtime/locator_issue_classifier.py

Locator issue classifier for Complete LLM Mode.

Source rule: P0 Scenarios Spec §5.3 (L478–490) — classify locator failures
into one of the 9 finite issue categories before attempting recovery or
asking the user for an alternative.

No LLM calls. No I/O. Deterministic keyword heuristics only.
When confidence < 0.5, callers should escalate to controller.call(purpose=...).

Controller integration (runtime_policy §15):
  Wrap with controller.call(purpose="locator_specialist", deterministic_safe=True)
  when telemetry is needed.  LLM escalation path lands in a separate wire-in slice.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Public enum tuple — taken verbatim from spec §5.3 (L481–489) + "unknown"
# for the no-match fallback.
# ---------------------------------------------------------------------------
LOCATOR_ISSUE_LABELS: tuple[str, ...] = (
    "locator_not_found",
    "locator_matches_multiple",
    "locator_matches_wrong_element",
    "locator_unstable",
    "locator_hidden",
    "locator_detached",
    "locator_scope_missing",
    "locator_text_mismatch",
    "locator_requires_frame_or_shadow",
    "unknown",
)

# ---------------------------------------------------------------------------
# Keyword signals (order = priority; first multi-keyword match wins)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    # locator_requires_frame_or_shadow — iframe / shadow DOM
    (("iframe", "frame", "shadow dom", "shadow-dom", "shadowroot", "shadow root",
      "inside frame", "in an iframe", "within frame"), "locator_requires_frame_or_shadow"),

    # locator_scope_missing — context/scope not set up
    (("scope missing", "context missing", "parent not found", "container not found",
      "no parent", "missing scope", "missing context", "no scope"), "locator_scope_missing"),

    # locator_matches_multiple — ambiguous match
    (("matches multiple", "multiple elements", "more than one", "ambiguous",
      "multiple matches", "several elements", "many elements", "duplicate locator",
      "strict mode violation"), "locator_matches_multiple"),

    # locator_matches_wrong_element — found but wrong
    (("wrong element", "wrong target", "incorrect element", "different element found",
      "matched wrong", "not the right element", "unexpected element",
      "matches wrong"), "locator_matches_wrong_element"),

    # locator_text_mismatch — text content doesn't match
    (("text mismatch", "text doesn't match", "label mismatch", "wrong text",
      "different text", "text changed", "label changed",
      "text content mismatch"), "locator_text_mismatch"),

    # locator_hidden — element exists but not visible
    (("hidden", "not visible", "invisible", "display none", "visibility hidden",
      "not displayed", "off screen", "outside viewport"), "locator_hidden"),

    # locator_detached — element removed from DOM
    (("detached", "removed from dom", "no longer in dom", "stale element",
      "element removed", "node detached", "dom detached"), "locator_detached"),

    # locator_unstable — flaky / dynamic element
    (("unstable", "flaky", "intermittent", "sometimes found", "dynamic id",
      "random id", "generated id", "changes on reload", "unpredictable",
      "non-deterministic"), "locator_unstable"),

    # locator_not_found — element simply absent
    (("not found", "no element", "element not found", "cannot find", "could not find",
      "locator not found", "no match", "zero results", "elementnotfound",
      "element does not exist"), "locator_not_found"),
]

_HIGH_CONFIDENCE = 0.85
_MED_CONFIDENCE = 0.65
_LOW_CONFIDENCE = 0.40


def _score_text(text_lower: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for kw in keywords if kw in text_lower)


def classify(text: str, ctx: dict | None = None) -> dict:  # noqa: ARG001
    """Classify a locator issue description.

    Parameters
    ----------
    text:
        Error message, locator debug output, or user description of the issue.
    ctx:
        Optional context dict (unused by heuristics; reserved for LLM escalation).

    Returns
    -------
    dict with keys:
        label      — one of LOCATOR_ISSUE_LABELS
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
