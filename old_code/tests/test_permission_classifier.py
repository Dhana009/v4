"""Unit tests for runtime.permission_classifier and related gateway helpers."""
from __future__ import annotations

import pytest

from runtime.permission_classifier import RISK_LABELS, classify_action_risk
from runtime.llm_policy_gateway import AUTONOMY_MODES, evaluate_permission


# ---------------------------------------------------------------------------
# 1. Safe action (assert_visible) in balanced → auto / safe_read_or_assert
# ---------------------------------------------------------------------------

def test_safe_assert_visible_balanced() -> None:
    result = classify_action_risk({"name": "assert_visible"}, "balanced")
    assert result["permission"] == "auto"
    assert result["risk"] == "safe_read_or_assert"


# ---------------------------------------------------------------------------
# 2. Medium action (click) in strict → ask
# ---------------------------------------------------------------------------

def test_click_strict_asks() -> None:
    result = classify_action_risk({"name": "click"}, "strict")
    assert result["permission"] == "ask"
    assert result["risk"] == "medium_browser_action"


# ---------------------------------------------------------------------------
# 3. High-risk (submit_order) in balanced → ask
# ---------------------------------------------------------------------------

def test_submit_order_balanced_asks() -> None:
    result = classify_action_risk({"name": "submit_order"}, "balanced")
    assert result["permission"] == "ask"
    assert result["risk"] == "high_risk_submit_upload_download"


# ---------------------------------------------------------------------------
# 4. Destructive (delete) in auto → deny
# ---------------------------------------------------------------------------

def test_delete_auto_denies() -> None:
    result = classify_action_risk({"name": "delete"}, "auto")
    assert result["permission"] == "deny"
    assert result["risk"] == "destructive_or_external_side_effect"


# ---------------------------------------------------------------------------
# 5. Unknown action → fallback medium / ask (balanced default)
# ---------------------------------------------------------------------------

def test_unknown_action_fallback_ask() -> None:
    result = classify_action_risk({"name": "do_something_weird"}, "balanced")
    assert result["permission"] == "ask"
    assert result["risk"] == "medium_browser_action"


# ---------------------------------------------------------------------------
# 6. evaluate_permission matches classify_action_risk output
# ---------------------------------------------------------------------------

def test_evaluate_permission_matches_classify() -> None:
    action = {"name": "click"}
    mode = "balanced"
    via_gateway = evaluate_permission(action, mode)
    via_classifier = classify_action_risk(action, mode)
    assert via_gateway == via_classifier


# ---------------------------------------------------------------------------
# 7. AUTONOMY_MODES tuple shape
# ---------------------------------------------------------------------------

def test_autonomy_modes_tuple_shape() -> None:
    assert isinstance(AUTONOMY_MODES, tuple)
    assert set(AUTONOMY_MODES) == {"strict", "balanced", "auto"}


# ---------------------------------------------------------------------------
# 8. RISK_LABELS tuple contains expected values
# ---------------------------------------------------------------------------

def test_risk_labels_tuple() -> None:
    assert isinstance(RISK_LABELS, tuple)
    assert "safe_read_or_assert" in RISK_LABELS
    assert "destructive_or_external_side_effect" in RISK_LABELS
