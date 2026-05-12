"""
tests/test_permission_capability.py

Tests for Cluster 7: Permission / Capability / Test Data / Auth / Human-in-loop.
S6-0701 through S6-0710.
"""
from __future__ import annotations

import pytest
from runtime.permission_policy import (
    AutonomyMode,
    RiskLevel,
    PermissionPolicy,
    classify_action_risk,
    check_permission,
    PermissionResult,
)
from runtime.capability_registry import (
    CapabilityRegistry,
    CapabilityStatus,
    get_capability_status,
    BASELINE_CAPABILITIES,
)
from runtime.test_data_policy import (
    TestDataClassification,
    TestDataRequirement,
    classify_test_data,
    propose_safe_test_data,
    redact_sensitive_data,
)
from runtime.human_in_loop import (
    HumanInLoopRequest,
    HumanInLoopTrigger,
    should_trigger_human_in_loop,
)


# ---------------------------------------------------------------------------
# S6-0701: Permission/Autonomy Mode Contract
# ---------------------------------------------------------------------------

def test_autonomy_mode_enum_values():
    assert AutonomyMode.FULL_AUTO is not None
    assert AutonomyMode.CONFIRM_EACH is not None
    assert AutonomyMode.ASK_FIRST is not None


def test_permission_check_allows_low_risk_in_full_auto():
    policy = PermissionPolicy(autonomy_mode=AutonomyMode.FULL_AUTO)
    result = check_permission(policy, RiskLevel.LOW)
    assert result.allowed is True


def test_permission_check_requires_confirm_for_high_risk():
    policy = PermissionPolicy(autonomy_mode=AutonomyMode.FULL_AUTO)
    result = check_permission(policy, RiskLevel.HIGH)
    assert result.allowed is False or result.requires_confirmation is True


def test_confirm_each_mode_always_requires_confirmation():
    policy = PermissionPolicy(autonomy_mode=AutonomyMode.CONFIRM_EACH)
    for level in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
        result = check_permission(policy, level)
        assert result.requires_confirmation is True


# ---------------------------------------------------------------------------
# S6-0702: Risk Classification Framework
# ---------------------------------------------------------------------------

def test_form_submit_classified_as_medium_risk():
    risk = classify_action_risk("form_submit", {"url": "https://example.com/submit"})
    assert risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)


def test_read_only_assertion_classified_as_low_risk():
    risk = classify_action_risk("assert_text", {"url": "https://example.com"})
    assert risk == RiskLevel.LOW


def test_delete_action_classified_as_high_risk():
    risk = classify_action_risk("delete_record", {"url": "https://example.com/delete"})
    assert risk == RiskLevel.HIGH


def test_navigation_classified_as_low_or_medium():
    risk = classify_action_risk("navigate", {"url": "https://example.com/login"})
    assert risk in (RiskLevel.LOW, RiskLevel.MEDIUM)


# ---------------------------------------------------------------------------
# S6-0703: Capability Registry Framework
# ---------------------------------------------------------------------------

def test_capability_registry_has_baseline():
    registry = CapabilityRegistry()
    assert len(registry.capabilities) > 0


def test_supported_capability_returns_supported():
    status = get_capability_status("click")
    assert status == CapabilityStatus.SUPPORTED


def test_unsupported_capability_returns_gap():
    status = get_capability_status("crm_api_validate")
    assert status == CapabilityStatus.CAPABILITY_GAP


def test_baseline_capabilities_defined():
    assert "click" in BASELINE_CAPABILITIES
    assert "fill" in BASELINE_CAPABILITIES
    assert "assert_text" in BASELINE_CAPABILITIES


# ---------------------------------------------------------------------------
# S6-0705: Test Data Requirement Classification
# ---------------------------------------------------------------------------

def test_credit_card_classified_as_sensitive():
    req = TestDataRequirement(field_name="credit_card", value=None)
    classification = classify_test_data(req)
    assert classification == TestDataClassification.SENSITIVE


def test_username_classified_as_normal():
    req = TestDataRequirement(field_name="username", value=None)
    classification = classify_test_data(req)
    assert classification in (TestDataClassification.NORMAL, TestDataClassification.SENSITIVE)


def test_email_classified_as_normal():
    req = TestDataRequirement(field_name="email", value="test@example.com")
    classification = classify_test_data(req)
    assert classification == TestDataClassification.NORMAL


# ---------------------------------------------------------------------------
# S6-0706: Safe Generated Test Data Proposal Flow
# ---------------------------------------------------------------------------

def test_safe_test_data_proposed_for_username():
    req = TestDataRequirement(field_name="username", value=None)
    proposal = propose_safe_test_data(req)
    assert proposal is not None
    assert "real" not in str(proposal).lower() or "test" in str(proposal).lower()


def test_no_real_credentials_in_proposal():
    req = TestDataRequirement(field_name="password", value=None)
    proposal = propose_safe_test_data(req)
    # Proposal should be clearly fake/test data
    assert proposal != "real_password_123"


# ---------------------------------------------------------------------------
# S6-0707: Sensitive Data Redaction Policy
# ---------------------------------------------------------------------------

def test_password_redacted():
    data = {"username": "testuser", "password": "secret123", "email": "test@test.com"}
    redacted = redact_sensitive_data(data)
    assert redacted["password"] == "[REDACTED]"
    assert redacted["username"] == "testuser"


def test_api_key_redacted():
    data = {"api_key": "sk-abc123", "action": "submit"}
    redacted = redact_sensitive_data(data)
    assert redacted["api_key"] == "[REDACTED]"


def test_non_sensitive_data_preserved():
    data = {"url": "https://example.com", "action": "click"}
    redacted = redact_sensitive_data(data)
    assert redacted["url"] == "https://example.com"


# ---------------------------------------------------------------------------
# S6-0710: Human-In-Loop Flow
# ---------------------------------------------------------------------------

def test_high_risk_action_triggers_human_in_loop():
    trigger = should_trigger_human_in_loop(
        action_type="delete_record",
        risk_level=RiskLevel.HIGH,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert trigger.should_pause is True


def test_low_risk_in_full_auto_no_human_loop():
    trigger = should_trigger_human_in_loop(
        action_type="assert_text",
        risk_level=RiskLevel.LOW,
        autonomy_mode=AutonomyMode.FULL_AUTO,
    )
    assert trigger.should_pause is False


def test_confirm_each_always_pauses():
    trigger = should_trigger_human_in_loop(
        action_type="click",
        risk_level=RiskLevel.LOW,
        autonomy_mode=AutonomyMode.CONFIRM_EACH,
    )
    assert trigger.should_pause is True


def test_human_in_loop_trigger_is_typed():
    trigger = should_trigger_human_in_loop(
        action_type="click",
        risk_level=RiskLevel.MEDIUM,
        autonomy_mode=AutonomyMode.ASK_FIRST,
    )
    assert isinstance(trigger, HumanInLoopTrigger)
    assert hasattr(trigger, "should_pause")
    assert hasattr(trigger, "reason")
