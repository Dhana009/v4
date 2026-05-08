from __future__ import annotations

import re
from typing import Any

# Sprint 3 INT-CALL-001: deterministic fast path for simple picked-element actions.
# Conditions for zero-LLM fast path (ALL three must be true):
#   1. Locator validates to exactly 1 visible/compatible element.
#   2. Action verb is in the deterministic action set.
#   3. User message has no compound/multi-step pattern.

DETERMINISTIC_ACTION_VERBS: frozenset[str] = frozenset({
    "click",
    "fill",
    "assert_visible",
    "assert visible",
    "assert_text",
    "assert text",
})

_COMPOUND_PATTERNS = re.compile(
    r"\b(and then|then verify|then check|and verify|and check|and validate|"
    r"then validate|submit after|after filling|this whole|everything on|"
    r"the entire|and submit|then submit)\b",
    re.IGNORECASE,
)

_MULTI_STEP_PATTERNS = re.compile(
    r"(,\s*(then|and|verify|check|validate)|(;\s*))",
    re.IGNORECASE,
)


def _is_compound_intent(user_message: str) -> bool:
    text = str(user_message or "").strip()
    if _COMPOUND_PATTERNS.search(text):
        return True
    if _MULTI_STEP_PATTERNS.search(text):
        return True
    return False


def _extract_action_verb(user_message: str) -> str | None:
    text = str(user_message or "").strip().lower()
    for verb in DETERMINISTIC_ACTION_VERBS:
        if verb in text:
            return verb
    return None


def classify_fast_path(
    *,
    user_message: str,
    locator_validated: bool,
    locator_count: int,
) -> tuple[bool, str]:
    """Return (qualifies, reason).

    qualifies=True means the fast path can be used (zero LLM calls).
    reason describes which condition failed if qualifies=False.
    """
    if _is_compound_intent(user_message):
        return False, "compound_intent"

    action_verb = _extract_action_verb(user_message)
    if action_verb is None:
        return False, "no_deterministic_action_verb"

    if not locator_validated or locator_count != 1:
        return False, f"locator_not_unique(count={locator_count})"

    return True, f"fast_path:{action_verb}"


def build_deterministic_plan(
    *,
    user_message: str,
    locator: str,
    action_verb: str,
    step_id: str | None = None,
    fill_value: str | None = None,
    expected_text: str | None = None,
) -> dict[str, Any]:
    """Build a minimal plan_ready payload without an LLM call."""
    normalized_verb = action_verb.replace(" ", "_").lower()

    step: dict[str, Any] = {
        "locator": locator,
        "action": normalized_verb,
        "source": "deterministic_fast_path",
    }
    if fill_value is not None:
        step["value"] = fill_value
    if expected_text is not None:
        step["expected_text"] = expected_text
    if step_id:
        step["id"] = step_id

    summary = f"{normalized_verb} on {locator}"
    return {
        "summary": summary,
        "steps": [step],
        "source": "deterministic_fast_path",
        "llm_calls": 0,
        "model_called": False,
    }
