"""
tests/test_context_policy.py

Tests for S6-0201: Context level policy enforcement.
Verifies L0-L5 context level definitions and purpose defaults.
"""
from __future__ import annotations

import pytest
from runtime.context_levels import CONTEXT_LEVELS, LEVEL_ORDER
from runtime.context_policy import (
    PURPOSE_CONTEXT_DEFAULTS,
    build_context_for_level,
    get_context_level_for_purpose,
)


# ---------------------------------------------------------------------------
# Unit tests: context level definitions
# ---------------------------------------------------------------------------

def test_all_six_levels_defined():
    for level in ("L0", "L1", "L2", "L3", "L4", "L5"):
        assert level in CONTEXT_LEVELS, f"Missing level {level}"


def test_l0_is_minimal():
    l0 = CONTEXT_LEVELS["L0"]
    assert l0["name"] == "user_message_only"
    assert "phase" in l0["includes"]


def test_l5_includes_raw_dom():
    l5 = CONTEXT_LEVELS["L5"]
    assert "raw_dom" in l5["includes"]


def test_level_order_is_ascending():
    # L0 < L1 < ... < L5
    for i in range(len(LEVEL_ORDER) - 1):
        a = LEVEL_ORDER[i]
        b = LEVEL_ORDER[i + 1]
        assert CONTEXT_LEVELS[a]["rank"] < CONTEXT_LEVELS[b]["rank"]


# ---------------------------------------------------------------------------
# Unit tests: purpose defaults
# ---------------------------------------------------------------------------

def test_intent_classifier_gets_l0_default():
    assert PURPOSE_CONTEXT_DEFAULTS["intent_classifier"] == "L0"


def test_page_validation_recommender_gets_l3_default():
    assert PURPOSE_CONTEXT_DEFAULTS["page_validation_recommender"] == "L3"


def test_recovery_diagnoser_gets_l4_default():
    assert PURPOSE_CONTEXT_DEFAULTS["recovery_diagnoser"] == "L4"


def test_all_14_purposes_have_context_default():
    from runtime.llm_purpose_policy import REQUIRED_PURPOSE_IDS
    for pid in REQUIRED_PURPOSE_IDS:
        assert pid in PURPOSE_CONTEXT_DEFAULTS, f"Missing context default for {pid}"


def test_get_context_level_for_purpose_returns_default():
    level = get_context_level_for_purpose("intent_classifier")
    assert level == "L0"


def test_get_context_level_for_purpose_allows_override():
    level = get_context_level_for_purpose("intent_classifier", override="L2")
    assert level == "L2"


def test_planning_purposes_never_get_l5_default():
    planning_purposes = [
        "intent_classifier",
        "clarification_generator",
        "journey_planner",
        "step_plan_normalizer",
        "plan_diff_editor",
    ]
    for pid in planning_purposes:
        level = PURPOSE_CONTEXT_DEFAULTS[pid]
        assert level != "L5", f"{pid} should not default to L5"


def test_execution_driver_never_gets_raw_dom():
    level = PURPOSE_CONTEXT_DEFAULTS["execution_driver"]
    assert level in ("L0", "L1", "L2")  # not L5


# ---------------------------------------------------------------------------
# Unit tests: context builders
# ---------------------------------------------------------------------------

def test_l0_context_contains_no_dom():
    page_state = {"phase": "planning", "modal_state": None, "dom": "<html>...</html>"}
    ctx = build_context_for_level("L0", page_state=page_state)
    assert "dom" not in ctx
    assert ctx["phase"] == "planning"


def test_l1_context_includes_element_descriptor():
    page_state = {"phase": "planning", "element": {"tag": "button", "text": "Submit", "position": (10, 20)}}
    ctx = build_context_for_level("L1", page_state=page_state)
    assert "element" in ctx
    assert ctx["element"]["tag"] == "button"


def test_l5_caps_raw_dom_at_50kb():
    big_dom = "x" * 100_000  # 100KB
    page_state = {"phase": "debug", "raw_dom": big_dom}
    ctx = build_context_for_level("L5", page_state=page_state)
    assert len(ctx.get("raw_dom", "")) <= 50 * 1024


def test_l5_excludes_secrets_and_credentials():
    page_state = {
        "phase": "debug",
        "raw_dom": "some dom",
        "password": "secret123",
        "api_key": "sk-abc",
        "token": "bearer xyz",
    }
    ctx = build_context_for_level("L5", page_state=page_state)
    assert "password" not in ctx
    assert "api_key" not in ctx
    assert "token" not in ctx


def test_context_builder_respects_level_ceiling():
    """L0 build should not include L2-level data even if present in page_state."""
    page_state = {
        "phase": "planning",
        "section_summary": "some section",
        "element": {"tag": "div"},
        "dom": "<html>",
    }
    ctx = build_context_for_level("L0", page_state=page_state)
    assert "dom" not in ctx
    assert "section_summary" not in ctx


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_purpose_policy_has_context_level():
    from runtime.llm_policy_registry import POLICY_REGISTRY
    for pid in POLICY_REGISTRY.list_purposes():
        policy = POLICY_REGISTRY.get(pid)
        assert "context_level" in policy["context_policy"], f"{pid} missing context_level"


def test_l0_contains_no_dom():
    ctx = build_context_for_level("L0", page_state={"phase": "planning"})
    assert "dom" not in ctx
    assert "raw_dom" not in ctx


def test_l3_context_has_page_intelligence_slot():
    """L3 build should include page_intelligence key (may be None if not available)."""
    ctx = build_context_for_level("L3", page_state={"phase": "planning"})
    assert "page_intelligence" in ctx


def test_l4_context_has_focused_error_packet():
    page_state = {"phase": "recovery", "error": "ElementNotFound", "trace": ["step1", "step2"]}
    ctx = build_context_for_level("L4", page_state=page_state)
    assert "error" in ctx or "failure_evidence" in ctx
