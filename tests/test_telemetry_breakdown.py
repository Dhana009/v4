from __future__ import annotations

from runtime.telemetry import (
    ModelCallTelemetry,
    record_model_call_start,
    record_model_call_end,
    _format_telemetry_line,
)
from runtime.skill_manager import SkillManager


def _make_messages():
    return [
        {"role": "system", "content": "You are an agent. " * 20},
        {"role": "user", "content": "Click the button."},
        {"role": "assistant", "content": "I will click it."},
        {"role": "tool", "tool_call_id": "t1", "content": "dom_result: " + "x" * 200},
    ]


def test_model_call_telemetry_has_breakdown_fields():
    record = record_model_call_start(
        call_id="test_001",
        purpose="main_orchestrator",
        model="gpt-4o-mini",
        messages=_make_messages(),
        tools=None,
        skill_count=2,
        skill_tokens=450,
    )
    assert record.system_prompt_tokens is not None
    assert record.system_prompt_tokens > 0
    assert record.skill_tokens == 450
    assert record.tool_schema_tokens is not None
    assert record.message_history_tokens is not None
    assert record.dom_or_tool_result_tokens is not None


def test_system_tokens_counted_separately_from_history():
    messages = [
        {"role": "system", "content": "System prompt " * 30},
        {"role": "user", "content": "User message " * 10},
        {"role": "assistant", "content": "Assistant response " * 10},
    ]
    record = record_model_call_start(
        call_id="test_002",
        purpose="main_orchestrator",
        model="gpt-4o-mini",
        messages=messages,
        tools=None,
    )
    assert record.system_prompt_tokens > 0
    assert record.message_history_tokens > 0
    assert record.system_prompt_tokens != record.message_history_tokens
    assert record.dom_or_tool_result_tokens == 0


def test_dom_tool_result_tokens_counted():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "tool", "tool_call_id": "t1", "content": "big dom result " * 50},
        {"role": "tool", "tool_call_id": "t2", "content": "another result " * 30},
    ]
    record = record_model_call_start(
        call_id="test_003",
        purpose="main_orchestrator",
        model="gpt-4o-mini",
        messages=messages,
        tools=None,
    )
    assert record.dom_or_tool_result_tokens > 0


def test_skill_tokens_from_skill_manager():
    sm = SkillManager()
    diag = sm.analyze(
        [("core", "core skill text " * 100), ("locator", "locator skill " * 50)],
        loaded_skill_names=["core", "locator"],
    )
    assert diag.estimated_total_skill_tokens > 0
    record = record_model_call_start(
        call_id="test_004",
        purpose="main_orchestrator",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        skill_tokens=diag.estimated_total_skill_tokens,
    )
    assert record.skill_tokens == diag.estimated_total_skill_tokens


def test_missing_token_categories_do_not_crash():
    record = record_model_call_start(
        call_id="test_005",
        purpose="main_orchestrator",
        model="gpt-4o-mini",
        messages=[],
        tools=None,
    )
    # all breakdown fields default to 0 or None — must not crash
    record_model_call_end(record, success=True)
    line = _format_telemetry_line(record)
    assert "[LLM_TELEMETRY]" in line


def test_telemetry_line_includes_skill_tokens_when_set():
    record = record_model_call_start(
        call_id="test_006",
        purpose="plan_diff_editor",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        skill_tokens=312,
    )
    record_model_call_end(record, success=True)
    line = _format_telemetry_line(record)
    assert "skill_tokens=312" in line
    assert "system_prompt_tokens=" in line
    assert "message_history_tokens=" in line
    assert "dom_or_tool_result_tokens=" in line


def test_telemetry_line_omits_none_skill_tokens():
    record = record_model_call_start(
        call_id="test_007",
        purpose="main_orchestrator",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        skill_tokens=None,
    )
    record_model_call_end(record, success=True)
    line = _format_telemetry_line(record)
    assert "skill_tokens=" not in line
