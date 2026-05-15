"""
runtime/permission_policy.py

Permission/autonomy mode contract and risk classification.

Source rule: S6-0701/0702 — autonomy modes, risk classification,
permission/capability baseline. High-risk actions require confirmation.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any


class AutonomyMode(enum.Enum):
    FULL_AUTO = "full_auto"       # Execute automatically unless high-risk
    CONFIRM_EACH = "confirm_each" # Confirm every action
    ASK_FIRST = "ask_first"       # Ask before any browser-changing action


class RiskLevel(enum.Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


@dataclass
class PermissionPolicy:
    autonomy_mode: AutonomyMode
    high_risk_threshold: RiskLevel = RiskLevel.HIGH


@dataclass
class PermissionResult:
    allowed: bool
    requires_confirmation: bool
    reason: str | None = None


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

_HIGH_RISK_ACTIONS: frozenset[str] = frozenset({
    "delete_record", "delete", "destroy", "drop", "truncate",
    "payment_submit", "purchase", "checkout_confirm",
    "send_email", "send_message",
})

_MEDIUM_RISK_ACTIONS: frozenset[str] = frozenset({
    "form_submit", "submit", "post_data", "upload_file",
    "update_record", "create_record", "fill_password",
})

_LOW_RISK_ACTIONS: frozenset[str] = frozenset({
    "click", "navigate", "scroll", "hover", "assert_text",
    "assert_visibility", "assert_attribute", "assert_count",
    "read_page", "screenshot",
})


def classify_action_risk(action_type: str, context: dict[str, Any] | None = None) -> RiskLevel:
    """Classify the risk level of an action type."""
    action_lower = action_type.lower()
    if action_lower in _HIGH_RISK_ACTIONS or "delete" in action_lower:
        return RiskLevel.HIGH
    if action_lower in _MEDIUM_RISK_ACTIONS:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def check_permission(policy: PermissionPolicy, risk_level: RiskLevel) -> PermissionResult:
    """Check if an action with *risk_level* is allowed under *policy*."""
    if policy.autonomy_mode == AutonomyMode.CONFIRM_EACH:
        return PermissionResult(
            allowed=True,
            requires_confirmation=True,
            reason="confirm_each_mode",
        )
    if policy.autonomy_mode == AutonomyMode.ASK_FIRST:
        return PermissionResult(
            allowed=True,
            requires_confirmation=True,
            reason="ask_first_mode",
        )
    # FULL_AUTO: allow low/medium, require confirmation for high
    if risk_level == RiskLevel.HIGH:
        return PermissionResult(
            allowed=False,
            requires_confirmation=True,
            reason="high_risk_action_requires_confirmation",
        )
    return PermissionResult(allowed=True, requires_confirmation=False)
