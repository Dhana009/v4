"""
runtime/failure_context.py

Failure context artifact — every failure must answer what was expected,
what happened, which layer failed, what evidence exists, and next legal actions.

Source rule: S6-1106.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NextLegalAction:
    action: str
    reason: str | None = None


@dataclass
class FailureContextArtifact:
    step_id: str
    expected: str
    actual: str
    layer: str
    evidence: dict[str, Any]
    next_actions: list[NextLegalAction] = field(default_factory=list)


_LAYER_ACTIONS: dict[str, list[str]] = {
    "browser": ["repair_locator", "retry", "ask_user"],
    "network": ["retry", "ask_user", "fail_closed"],
    "runtime": ["ask_user", "fail_closed"],
    "assertion": ["ask_user", "fail_closed"],
}

_ERROR_ACTIONS: dict[str, list[str]] = {
    "elementnotfounderror": ["repair_locator", "retry", "ask_user"],
    "timeouterror": ["retry", "ask_user"],
    "networkerror": ["retry", "fail_closed"],
    "assertionerror": ["ask_user", "fail_closed"],
}


def build_failure_context(
    step_id: str,
    expected: str,
    actual: str,
    layer: str,
    evidence: dict[str, Any],
) -> FailureContextArtifact:
    # Determine next actions from error and layer
    actual_lower = actual.lower()
    actions: list[str] = []
    for pattern, acts in _ERROR_ACTIONS.items():
        if pattern in actual_lower:
            actions = acts
            break
    if not actions:
        actions = _LAYER_ACTIONS.get(layer, ["ask_user", "fail_closed"])

    next_actions = [NextLegalAction(action=a) for a in actions]
    return FailureContextArtifact(
        step_id=step_id,
        expected=expected,
        actual=actual,
        layer=layer,
        evidence=evidence,
        next_actions=next_actions,
    )
