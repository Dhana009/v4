from __future__ import annotations

from agent import AgentLoop
from runtime.deterministic_fast_path import (
    classify_fast_path,
    build_deterministic_plan,
    _is_compound_intent,
    _extract_action_verb,
)


# --- classify_fast_path ---

def test_simple_click_unique_locator_qualifies():
    qualifies, reason = classify_fast_path(
        user_message="click the submit button",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True
    assert "fast_path" in reason


def test_simple_assert_visible_qualifies():
    qualifies, reason = classify_fast_path(
        user_message="assert visible the heading",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True


def test_simple_fill_qualifies():
    qualifies, reason = classify_fast_path(
        user_message="fill the email input",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True


def test_compound_intent_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="click this and then verify the next page",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "compound_intent"


def test_fill_and_submit_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="fill this form and submit",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "compound_intent"


def test_check_everything_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="check everything on this page",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "compound_intent"


def test_multi_match_locator_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="click the button",
        locator_validated=True,
        locator_count=3,
    )
    assert qualifies is False
    assert "locator_not_unique" in reason


def test_zero_match_locator_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="click the button",
        locator_validated=False,
        locator_count=0,
    )
    assert qualifies is False
    assert "locator_not_unique" in reason


def test_unknown_action_verb_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="hover over the menu",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "no_deterministic_action_verb"


def test_whole_section_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="test this whole section",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False


def test_multi_step_with_semicolon_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="click this; verify the result",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "compound_intent"


# --- build_deterministic_plan ---

def test_plan_has_zero_llm_calls():
    plan = build_deterministic_plan(
        user_message="click the button",
        locator="button[data-testid='submit']",
        action_verb="click",
    )
    assert plan["llm_calls"] == 0
    assert plan["model_called"] is False


def test_plan_includes_locator_and_action():
    plan = build_deterministic_plan(
        user_message="click the submit button",
        locator="button[data-testid='submit']",
        action_verb="click",
    )
    assert len(plan["steps"]) == 1
    step = plan["steps"][0]
    child = step["children"][0]
    assert step["step_id"] == "1"
    assert step["kind"] == "step"
    assert step["type"] == "step"
    assert child["locator"] == "button[data-testid='submit']"
    assert child["type"] == "click"
    assert child["operation_id"] == "op_1"
    assert child["status"] == "planned"


def test_plan_source_is_deterministic():
    plan = build_deterministic_plan(
        user_message="assert visible heading",
        locator="h1",
        action_verb="assert_visible",
    )
    assert plan["source"] == "deterministic_fast_path"


def test_plan_fill_includes_value():
    plan = build_deterministic_plan(
        user_message="fill the email input",
        locator="input[name='email']",
        action_verb="fill",
        fill_value="test@example.com",
    )
    child = plan["steps"][0]["children"][0]
    assert child["type"] == "fill"
    assert child["value"] == "test@example.com"
    assert plan["steps"][0]["expected_outcome"]["type"] == "content_change"


def test_plan_assert_text_includes_expected():
    plan = build_deterministic_plan(
        user_message="assert text of heading",
        locator="h1",
        action_verb="assert_text",
        expected_text="Welcome",
    )
    child = plan["steps"][0]["children"][0]
    assert child["type"] == "assert"
    assert child["assertion"] == "has_text"
    assert child["expected_value"] == "Welcome"
    assert child["value"] == "Welcome"


def test_plan_assert_visible_has_assertion_child():
    plan = build_deterministic_plan(
        user_message="assert visible heading",
        locator="h1",
        action_verb="assert_visible",
    )
    child = plan["steps"][0]["children"][0]
    assert child["type"] == "assert"
    assert child["assertion"] == "visible"


def test_plan_is_compatible_with_confirmed_execution_contract():
    payload = build_deterministic_plan(
        user_message="assert text of heading",
        locator="h1",
        action_verb="assert_text",
        step_id="step-1",
        expected_text="Welcome",
    )
    loop = AgentLoop.__new__(AgentLoop)
    loop.confirmed_plan_by_step_id = {}
    loop.confirmed_plan_step_ids = []
    loop.confirmed_child_results_by_step_id = {}
    loop.confirmed_execution_mismatch_count_by_step_id = {}

    confirmed_plan = loop._build_confirmed_execution_plan(payload, source_plan_state=payload)

    assert confirmed_plan["target_step_id"] == "step-1"
    assert confirmed_plan["steps"][0]["step_id"] == "step-1"
    assert confirmed_plan["steps"][0]["children"][0]["operation_id"] == "op_1"
    assert confirmed_plan["steps"][0]["children"][0]["type"] == "assert"
    assert confirmed_plan["steps"][0]["children"][0]["assertion"] == "has_text"
    assert confirmed_plan["steps"][0]["children"][0]["expected_value"] == "Welcome"


def test_confirmation_gate_not_bypassed():
    """The plan payload has model_called=False, but plan_ready still goes through
    _send_plan_ready_after_confirmation which requires user confirmation. This test
    verifies the payload does NOT auto-execute (no 'confirmed' key set)."""
    plan = build_deterministic_plan(
        user_message="click button",
        locator="button",
        action_verb="click",
    )
    assert "confirmed" not in plan
    assert plan.get("model_called") is False


# --- helpers ---

def test_is_compound_intent_detects_and_then():
    assert _is_compound_intent("click this and then verify") is True


def test_is_compound_intent_clean_message():
    assert _is_compound_intent("click the submit button") is False


def test_extract_action_verb_click():
    assert _extract_action_verb("click the button") == "click"


def test_extract_action_verb_fill():
    assert _extract_action_verb("fill the input with test") == "fill"


def test_extract_action_verb_unknown():
    assert _extract_action_verb("hover over element") is None
