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
    if "exact text" in text or "assert text" in text:
        return "assert_text"
    if "visible" in text and any(keyword in text for keyword in ("assert", "verify", "check", "validate")):
        return "assert_visible"
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
    target_label: str | None = None,
    fill_value: str | None = None,
    expected_text: str | None = None,
) -> dict[str, Any]:
    """Build a backend-compatible plan_ready payload without an LLM call."""
    normalized_verb = action_verb.replace(" ", "_").lower()
    resolved_step_id = str(step_id or "1").strip() or "1"
    target = str(target_label or "").strip() or locator

    child_type = "assert" if normalized_verb in {"assert_visible", "assert_text"} else normalized_verb
    child: dict[str, Any] = {
        "operation_id": "op_1",
        "type": child_type,
        "description": _build_child_description(
            normalized_verb,
            target=target,
            fill_value=fill_value,
            expected_text=expected_text,
        ),
        "target": target,
        "locator": locator,
        "status": "planned",
    }
    if normalized_verb == "fill" and fill_value is not None:
        child["value"] = fill_value
    if normalized_verb == "assert_visible":
        child["assertion"] = "visible"
    if normalized_verb == "assert_text":
        child["assertion"] = "has_text"
        if expected_text is not None:
            child["value"] = expected_text
            child["expected_value"] = expected_text

    step: dict[str, Any] = {
        "step_id": resolved_step_id,
        "step_number": 1,
        "intent": str(user_message or "").strip(),
        "expected_outcome": _build_expected_outcome(normalized_verb, target=target),
        "status": "planned",
        "kind": "step",
        "type": "step",
        "text": str(user_message or "").strip(),
        "label": str(user_message or "").strip(),
        "title": str(user_message or "").strip(),
        "children": [child],
    }

    summary = child["description"]
    return {
        "plan_id": f"deterministic-{resolved_step_id}",
        "original_user_intent": str(user_message or "").strip(),
        "summary": summary,
        "steps": [step],
        "step_ids": [resolved_step_id],
        "target_step_id": resolved_step_id,
        "source": "deterministic_fast_path",
        "llm_calls": 0,
        "model_called": False,
    }


def _build_expected_outcome(action_verb: str, *, target: str) -> dict[str, Any]:
    if action_verb == "click":
        return {
            "type": "not_sure",
            "description": f"click result for {target} will be confirmed during execution",
            "source": "user",
            "required": True,
        }
    if action_verb == "fill":
        return {
            "type": "content_change",
            "description": f"{target} receives the provided value",
            "source": "user",
            "required": False,
        }
    return {
        "type": "no_visible_change",
        "description": f"{target} is validated in place",
        "source": "user",
        "required": False,
    }


def _build_child_description(
    action_verb: str,
    *,
    target: str,
    fill_value: str | None,
    expected_text: str | None,
) -> str:
    if action_verb == "click":
        return f"Click {target}"
    if action_verb == "fill":
        return f"Fill {target}"
    if action_verb == "assert_visible":
        return f"{target} is visible"
    if action_verb == "assert_text" and expected_text:
        return f'{target} has text "{expected_text}"'
    return f"{action_verb} on {target}"
