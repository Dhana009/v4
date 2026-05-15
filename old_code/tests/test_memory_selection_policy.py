"""
tests/test_memory_selection_policy.py

Tests for S6-0204: Memory selection policy.
Verifies per-purpose memory selection, exclusions, and size limits.
"""
from __future__ import annotations

import pytest
from runtime.memory_selection_policy import (
    MEMORY_SELECTION_DEFAULTS,
    MemoryItem,
    select_memory_for_purpose,
)


def _item(category: str, content: str, tokens: int = 100) -> MemoryItem:
    return MemoryItem(category=category, content=content, tokens=tokens)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_full_chat_history_not_sent_by_default():
    all_memory = [
        _item("chat_history", "old message 1"),
        _item("chat_history", "old message 2"),
        _item("user_message", "current message"),
    ]
    selected = select_memory_for_purpose("intent_classifier", all_memory)
    categories = [m.category for m in selected]
    assert "chat_history" not in categories
    assert "user_message" in categories


def test_old_plans_excluded_unless_relevant():
    all_memory = [
        _item("old_plan", "previous plan data"),
        _item("user_message", "current message"),
        _item("current_plan", "active plan"),
    ]
    selected = select_memory_for_purpose("intent_classifier", all_memory)
    categories = [m.category for m in selected]
    assert "old_plan" not in categories


def test_execution_traces_excluded_unless_debugging():
    all_memory = [
        _item("execution_trace", "step trace"),
        _item("user_message", "message"),
    ]
    selected = select_memory_for_purpose("intent_classifier", all_memory)
    categories = [m.category for m in selected]
    assert "execution_trace" not in categories


def test_recovery_purpose_includes_recent_trace():
    all_memory = [
        _item("error_context", "error info"),
        _item("recent_trace", "last 3 steps"),
        _item("chat_history", "old chat"),
    ]
    selected = select_memory_for_purpose("recovery_diagnoser", all_memory)
    categories = [m.category for m in selected]
    assert "error_context" in categories
    assert "recent_trace" in categories
    assert "chat_history" not in categories


def test_memory_selection_per_purpose_correct():
    # step_plan_normalizer should get current_plan, page_state, user_message
    all_memory = [
        _item("user_message", "normalize this step"),
        _item("current_plan", "plan data"),
        _item("page_state", "page info"),
        _item("chat_history", "old"),
        _item("old_plan", "old plan"),
    ]
    selected = select_memory_for_purpose("step_plan_normalizer", all_memory)
    categories = [m.category for m in selected]
    assert "user_message" in categories
    assert "current_plan" in categories
    assert "page_state" in categories
    assert "chat_history" not in categories


def test_secrets_excluded_from_memory():
    all_memory = [
        _item("user_message", "click login"),
        _item("credentials", "password=secret"),
        _item("api_keys", "sk-abc123"),
    ]
    selected = select_memory_for_purpose("intent_classifier", all_memory)
    categories = [m.category for m in selected]
    assert "credentials" not in categories
    assert "api_keys" not in categories


def test_maximum_memory_size_enforced():
    # Create many items that exceed 20000 tokens
    all_memory = [_item("user_message", f"msg {i}", tokens=3000) for i in range(10)]
    selected = select_memory_for_purpose("intent_classifier", all_memory, max_tokens=20000)
    total = sum(m.tokens for m in selected)
    assert total <= 20000


def test_memory_selection_logged_with_reason():
    all_memory = [_item("user_message", "test")]
    import runtime.memory_selection_policy as msp
    msp.clear_selection_log()
    select_memory_for_purpose("intent_classifier", all_memory)
    log = msp.get_selection_log()
    assert len(log) >= 1
    entry = log[-1]
    assert "purpose" in entry
    assert "selected_categories" in entry


def test_all_14_purposes_have_memory_defaults():
    from runtime.llm_purpose_policy import REQUIRED_PURPOSE_IDS
    for pid in REQUIRED_PURPOSE_IDS:
        assert pid in MEMORY_SELECTION_DEFAULTS, f"Missing memory selection for {pid}"


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_step_planning_includes_only_current_plan():
    all_memory = [
        _item("user_message", "step"),
        _item("current_plan", "plan"),
        _item("old_plan", "old"),
    ]
    selected = select_memory_for_purpose("step_plan_normalizer", all_memory)
    categories = [m.category for m in selected]
    assert "old_plan" not in categories
    assert "current_plan" in categories


def test_replay_repair_includes_replay_failure():
    all_memory = [
        _item("original_trace", "recorded actions"),
        _item("replay_failure", "step 3 failed"),
        _item("chat_history", "old"),
    ]
    selected = select_memory_for_purpose("replay_repair_specialist", all_memory)
    categories = [m.category for m in selected]
    assert "original_trace" in categories
    assert "replay_failure" in categories
