"""
runtime/journey_classifier.py

Journey intent classifier for Complete LLM Mode.

Source rule: S6-0401 — classify broad user requests into full_journey_automation.
No immediate execution. Clarification for missing data/scope/permissions.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class IntentType(enum.Enum):
    FULL_JOURNEY_AUTOMATION = "full_journey_automation"
    SINGLE_ACTION = "single_action"
    RECOMMENDATION_REQUEST = "recommendation_request"
    STEPS_MODE = "steps_mode"
    UNKNOWN = "unknown"


@dataclass
class JourneyClassification:
    intent_type: IntentType
    next_action: str           # "clarification_needed" | "page_analysis_requested" | "draft_plan_requested" | "execution_started" | "test_data_required"
    requires_clarification: bool
    missing_fields: list[str]
    has_capability_risks: bool
    clarification_message: str | None = None


# ---------------------------------------------------------------------------
# Keyword signals
# ---------------------------------------------------------------------------

_JOURNEY_KEYWORDS = frozenset({
    "journey", "flow", "automation", "smoke test", "test for", "test the",
    "automate", "entire", "full", "multi-step", "end-to-end", "e2e",
    "multi page", "multi-page",
})

_SINGLE_ACTION_KEYWORDS = frozenset({
    "click", "fill", "type", "check", "verify", "assert", "navigate",
})

_RECOMMENDATION_KEYWORDS = frozenset({
    "recommend", "suggest", "what should", "validate this page",
    "check this page", "analyze the page",
})

_CAPABILITY_RISK_KEYWORDS = frozenset({
    "crm", "salesforce", "api", "graphql", "database", "sql",
    "external service", "third party",
})

_TEST_DATA_KEYWORDS = frozenset({
    "upload", "file", "checkout", "pay", "credit card", "purchase",
    "billing", "payment",
})


def classify_journey_intent(
    user_message: str,
    context: dict[str, Any] | None = None,
) -> JourneyClassification:
    """Classify user intent from *user_message*.

    Returns JourneyClassification with next_action and clarification flags.
    """
    ctx = context or {}
    msg_lower = user_message.lower().strip()

    # Empty input → clarification required
    if not msg_lower:
        return JourneyClassification(
            intent_type=IntentType.UNKNOWN,
            next_action="clarification_needed",
            requires_clarification=True,
            missing_fields=["user_goal"],
            has_capability_risks=False,
            clarification_message="Could you describe what you want to test?",
        )

    # Check for recommendation request
    if any(kw in msg_lower for kw in _RECOMMENDATION_KEYWORDS):
        return JourneyClassification(
            intent_type=IntentType.RECOMMENDATION_REQUEST,
            next_action="page_analysis_requested",
            requires_clarification=False,
            missing_fields=[],
            has_capability_risks=False,
        )

    # Check for single action
    words = set(msg_lower.split())
    is_single = any(kw in msg_lower for kw in _SINGLE_ACTION_KEYWORDS)
    is_journey = any(kw in msg_lower for kw in _JOURNEY_KEYWORDS)

    if is_single and not is_journey:
        return JourneyClassification(
            intent_type=IntentType.SINGLE_ACTION,
            next_action="clarification_needed",
            requires_clarification=False,
            missing_fields=[],
            has_capability_risks=False,
        )

    # Check capability risks
    has_capability_risks = any(kw in msg_lower for kw in _CAPABILITY_RISK_KEYWORDS)

    # Check for missing test data
    needs_test_data = any(kw in msg_lower for kw in _TEST_DATA_KEYWORDS)
    missing_fields: list[str] = []
    if needs_test_data:
        missing_fields.append("test_data")

    # Determine next_action for journey
    target_pages = ctx.get("target_pages")
    if missing_fields:
        next_action = "test_data_required" if "test_data" in missing_fields else "clarification_needed"
        requires_clarification = True
    elif target_pages:
        next_action = "draft_plan_requested"
        requires_clarification = False
    else:
        next_action = "page_analysis_requested"
        requires_clarification = False

    return JourneyClassification(
        intent_type=IntentType.FULL_JOURNEY_AUTOMATION,
        next_action=next_action,
        requires_clarification=requires_clarification,
        missing_fields=missing_fields,
        has_capability_risks=has_capability_risks,
    )
