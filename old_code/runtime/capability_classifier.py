"""
runtime/capability_classifier.py

Capability / risk classifier for Complete LLM Mode.

Source rule: P0 Scenarios Spec §5.5 (L508–517) — classify each planned
operation into a risk tier before execution or plan confirmation.

No LLM calls. No I/O. Deterministic keyword heuristics only.
When confidence < 0.5, callers should escalate to controller.call(purpose=...).

Controller integration (runtime_policy §15):
  Wrap with controller.call(purpose="capability_handler", deterministic_safe=True)
  when telemetry is needed.  LLM escalation path lands in a separate wire-in slice.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Public enum tuple — taken verbatim from spec §5.5 (L511–516) + "unknown"
# for the no-match fallback.
# ---------------------------------------------------------------------------
CAPABILITY_LABELS: tuple[str, ...] = (
    "safe_read_or_assert",
    "medium_browser_action",
    "high_risk_submit_upload_download",
    "destructive_or_external_side_effect",
    "unsupported_capability",
    "requires_human_input",
    "unknown",
)

# ---------------------------------------------------------------------------
# Keyword signals (order = priority; higher-risk labels checked first so they
# take precedence over lower-risk ones for ambiguous inputs)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    # unsupported_capability — system cannot do it at all
    (("not supported", "unsupported", "cannot verify", "can't verify",
      "file content verification", "pdf content", "out of scope",
      "not implemented", "capability gap", "no tool for",
      "missing tool"), "unsupported_capability"),

    # requires_human_input — needs a human in the loop
    (("requires human", "need human", "human input", "human approval",
      "manual approval", "captcha", "2fa", "two factor", "mfa",
      "authentication required", "otp", "one time password",
      "human verification"), "requires_human_input"),

    # destructive_or_external_side_effect — external APIs, databases, CRM, money
    (("delete", "destroy", "drop table", "truncate", "purge", "wipe",
      "external api", "third party api", "crm", "salesforce", "graphql mutation",
      "database write", "sql insert", "sql update", "sql delete",
      "send email", "send sms", "external service", "payment gateway",
      "charge card", "debit", "irreversible"), "destructive_or_external_side_effect"),

    # high_risk_submit_upload_download — submit forms, upload files, download
    (("submit", "upload", "download", "file upload", "attach file",
      "checkout", "place order", "purchase", "pay", "credit card",
      "billing", "buy now", "confirm order", "book", "reserve",
      "schedule appointment"), "high_risk_submit_upload_download"),

    # medium_browser_action — navigation, clicks, fills that change state
    (("click", "fill", "type", "select", "navigate", "go to", "open page",
      "enter text", "clear field", "focus", "hover", "drag", "drop",
      "scroll", "search", "login", "sign in", "log in",
      "change dropdown", "toggle"), "medium_browser_action"),

    # safe_read_or_assert — read-only checks and assertions
    (("assert", "verify", "check", "read", "inspect", "validate", "expect",
      "should be", "should contain", "should equal", "should have",
      "get text", "get value", "count elements", "snapshot",
      "screenshot"), "safe_read_or_assert"),
]

_HIGH_CONFIDENCE = 0.85
_MED_CONFIDENCE = 0.65
_LOW_CONFIDENCE = 0.40


def _score_text(text_lower: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for kw in keywords if kw in text_lower)


def classify(text: str, ctx: dict | None = None) -> dict:  # noqa: ARG001
    """Classify the capability/risk level of a requested operation.

    Parameters
    ----------
    text:
        User message, planned action description, or step instruction.
    ctx:
        Optional context dict (unused by heuristics; reserved for LLM escalation).

    Returns
    -------
    dict with keys:
        label      — one of CAPABILITY_LABELS
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
