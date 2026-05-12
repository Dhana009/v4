"""
tests/test_human_in_loop.py

Dedicated behavioral tests for runtime/human_in_loop.py.

Source rules: S6-0710 — human-in-loop flow with typed trigger.
High-risk actions and confirm_each mode must pause for human confirmation.
"""
from __future__ import annotations

import pytest

from runtime.human_in_loop import (
    HumanInLoopTrigger,
    HumanInLoopRequest,
    should_trigger_human_in_loop,
)
from runtime.permission_policy import AutonomyMode, RiskLevel


# ---------------------------------------------------------------------------
# 1. CONFIRM_EACH mode always pauses regardless of risk
# ---------------------------------------------------------------------------

def test_confirm_each_always_pauses_low_risk():
    trigger = should_trigger_human_in_loop(
        action_type="click",
        risk_level=RiskLevel.LOW,
        autonomy_mode=AutonomyMode.CONFIRM_EACH,
    )
    assert trigger.should_pause is True
    assert trigger.reason is not None


def test_confirm_each_always_pauses_medium_risk():
    trigger = should_trigger_human_in_loop(
        action_type="fill_form",
        risk_level=RiskLevel.MEDIUM,
        autonomy_mode=AutonomyMode.CONFIRM_EACH,
    )
    assert trigger.should_pause is True


def test_confirm_each_always_pauses_high_risk():
    trigger = should_trigger_human_in_loop(
        action_type="delete_record",
        risk_level=RiskLevel.HIGH,
        autonomy_mode=AutonomyMode.CONFIRM_EACH,
    )
    assert trigger.should_pause is True


# ---------------------------------------------------------------------------
# 2. ASK_FIRST mode pauses
# ---------------------------------------------------------------------------

def test_ask_first_pauses():
    trigger = should_trigger_human_in_loop(
        action_type="navigate",
        risk_level=RiskLevel.LOW,
        autonomy_mode=AutonomyMode.ASK_FIRST,
    )
    assert trigger.should_pause is True
    assert trigger.reason is not None


# ---------------------------------------------------------------------------
# 3. FULL_AUTO mode: only pauses for HIGH risk
# ---------------------------------------------------------------------------

def test_full_auto_does_not_pause_for_low_risk():
    trigger = should_trigger_human_in_loop(
        action_type="click",
        risk_level=RiskLevel.LOW,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert trigger.should_pause is False
    assert trigger.reason is None


def test_full_auto_does_not_pause_for_medium_risk():
    trigger = should_trigger_human_in_loop(
        action_type="fill_form",
        risk_level=RiskLevel.MEDIUM,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert trigger.should_pause is False


def test_full_auto_pauses_for_high_risk():
    trigger = should_trigger_human_in_loop(
        action_type="payment_submit",
        risk_level=RiskLevel.HIGH,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert trigger.should_pause is True
    assert trigger.reason is not None


# ---------------------------------------------------------------------------
# 4. Trigger carries action_type through
# ---------------------------------------------------------------------------

def test_trigger_preserves_action_type_when_paused():
    trigger = should_trigger_human_in_loop(
        action_type="send_email",
        risk_level=RiskLevel.HIGH,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert trigger.action_type == "send_email"


def test_trigger_preserves_action_type_when_not_paused():
    trigger = should_trigger_human_in_loop(
        action_type="read_dom",
        risk_level=RiskLevel.LOW,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert trigger.action_type == "read_dom"


# ---------------------------------------------------------------------------
# 5. Return type is always HumanInLoopTrigger
# ---------------------------------------------------------------------------

def test_return_type_is_trigger():
    for autonomy in AutonomyMode:
        for risk in RiskLevel:
            result = should_trigger_human_in_loop(
                action_type="test_action",
                risk_level=risk,
                autonomy_mode=autonomy,
            )
            assert isinstance(result, HumanInLoopTrigger)


# ---------------------------------------------------------------------------
# 6. HumanInLoopRequest dataclass carries typed fields
# ---------------------------------------------------------------------------

def test_human_in_loop_request_fields():
    req = HumanInLoopRequest(
        action_type="delete_record",
        risk_level=RiskLevel.HIGH,
        autonomy_mode=AutonomyMode.CONFIRM_EACH,
        context={"step_id": "step-001", "run_id": "run-abc"},
    )
    assert req.action_type == "delete_record"
    assert req.risk_level == RiskLevel.HIGH
    assert req.autonomy_mode == AutonomyMode.CONFIRM_EACH
    assert req.context["step_id"] == "step-001"


def test_human_in_loop_request_context_optional():
    req = HumanInLoopRequest(
        action_type="click",
        risk_level=RiskLevel.LOW,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert req.context is None


# ---------------------------------------------------------------------------
# 7. No secrets or manual codes in test data
# ---------------------------------------------------------------------------

def test_no_raw_secrets_in_test_data():
    """Test data in this file must not embed raw credentials."""
    contexts = [
        {"step_id": "step-001", "run_id": "run-abc"},
        None,
    ]
    for ctx in contexts:
        if ctx:
            for val in ctx.values():
                assert "password" not in str(val).lower()
                assert "otp" not in str(val).lower()
                assert "sk-" not in str(val)


# ---------------------------------------------------------------------------
# 8. Cancel/no-pause path has reason=None
# ---------------------------------------------------------------------------

def test_no_pause_reason_is_none():
    trigger = should_trigger_human_in_loop(
        action_type="assert_text",
        risk_level=RiskLevel.LOW,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert trigger.should_pause is False
    assert trigger.reason is None


# ---------------------------------------------------------------------------
# 9. Pause reason is non-empty string when paused
# ---------------------------------------------------------------------------

def test_pause_reason_is_non_empty_string():
    for autonomy in [AutonomyMode.CONFIRM_EACH, AutonomyMode.ASK_FIRST]:
        trigger = should_trigger_human_in_loop(
            action_type="navigate",
            risk_level=RiskLevel.LOW,
            autonomy_mode=autonomy,
        )
        assert isinstance(trigger.reason, str)
        assert len(trigger.reason) > 0


def test_high_risk_pause_reason_non_empty():
    trigger = should_trigger_human_in_loop(
        action_type="drop_table",
        risk_level=RiskLevel.HIGH,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert isinstance(trigger.reason, str)
    assert len(trigger.reason) > 0
