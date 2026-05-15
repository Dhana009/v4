"""
runtime/human_in_loop.py

Human-in-the-loop flow: pause triggers for high-risk actions and confirm_each mode.

Source rule: S6-0710 — human-in-loop flow with typed trigger.
"""
from __future__ import annotations

from dataclasses import dataclass
from runtime.permission_policy import AutonomyMode, RiskLevel


@dataclass
class HumanInLoopTrigger:
    should_pause: bool
    reason: str | None
    action_type: str | None = None


@dataclass
class HumanInLoopRequest:
    action_type: str
    risk_level: RiskLevel
    autonomy_mode: AutonomyMode
    context: dict | None = None


def should_trigger_human_in_loop(
    action_type: str,
    risk_level: RiskLevel,
    autonomy_mode: AutonomyMode,
) -> HumanInLoopTrigger:
    """Determine if human confirmation is needed before executing *action_type*."""
    if autonomy_mode == AutonomyMode.CONFIRM_EACH:
        return HumanInLoopTrigger(
            should_pause=True,
            reason="confirm_each_mode_always_pauses",
            action_type=action_type,
        )
    if autonomy_mode == AutonomyMode.ASK_FIRST:
        return HumanInLoopTrigger(
            should_pause=True,
            reason="ask_first_mode",
            action_type=action_type,
        )
    # FULL_AUTO: only pause for HIGH risk
    if risk_level == RiskLevel.HIGH:
        return HumanInLoopTrigger(
            should_pause=True,
            reason="high_risk_action_requires_human_confirmation",
            action_type=action_type,
        )
    return HumanInLoopTrigger(
        should_pause=False,
        reason=None,
        action_type=action_type,
    )
