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


# ---------------------------------------------------------------------------
# S5-007: new attribution fields
# ---------------------------------------------------------------------------

def test_new_attribution_fields_accepted_by_record_model_call_start():
    record = record_model_call_start(
        call_id="s5_007_001",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this"}],
        tools=None,
        prompt_pack_id="planning_pack_v1",
        prompt_pack_version=1,
        skills_loaded=["llm_runtime_controller", "prompt_persona_skill_loading"],
        skill_levels=["core_compact", "core_compact"],
        model_class="main",
        context_bucket="planning",
        cached_tokens=0,
        prefix_hash="abc123",
    )
    assert record.prompt_pack_id == "planning_pack_v1"
    assert record.prompt_pack_version == 1
    assert record.skills_loaded == ["llm_runtime_controller", "prompt_persona_skill_loading"]
    assert record.skill_levels == ["core_compact", "core_compact"]
    assert record.model_class == "main"
    assert record.context_bucket == "planning"
    assert record.cached_tokens == 0
    assert record.prefix_hash == "abc123"


def test_attribution_fields_default_to_none():
    record = record_model_call_start(
        call_id="s5_007_002",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
    )
    assert record.prompt_pack_id is None
    assert record.prompt_pack_version is None
    assert record.skills_loaded is None
    assert record.skill_levels is None
    assert record.model_class is None
    assert record.context_bucket is None
    assert record.cached_tokens is None
    assert record.prefix_hash is None


def test_telemetry_line_includes_new_fields_when_set():
    record = record_model_call_start(
        call_id="s5_007_003",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        prompt_pack_id="planning_pack_v1",
        skills_loaded=["llm_runtime_controller"],
        skill_levels=["core_compact"],
        model_class="main",
        context_bucket="planning",
        cached_tokens=40,
        prefix_hash="deadbeef",
    )
    record_model_call_end(record, success=True)
    line = _format_telemetry_line(record)
    assert "prompt_pack_id=planning_pack_v1" in line
    assert "model_class=main" in line
    assert "context_bucket=planning" in line
    assert "cached_tokens=40" in line
    assert "skills_loaded=llm_runtime_controller" in line
    assert "skill_levels=core_compact" in line
    assert "prefix_hash=deadbeef" in line


def test_telemetry_line_omits_none_attribution_fields():
    record = record_model_call_start(
        call_id="s5_007_004",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
    )
    record_model_call_end(record, success=True)
    line = _format_telemetry_line(record)
    assert "prompt_pack_id=" not in line
    assert "model_class=" not in line
    assert "context_bucket=" not in line
    assert "cached_tokens=" not in line
    assert "skills_loaded=" not in line
    assert "skill_levels=" not in line
    assert "prefix_hash=" not in line


def test_cached_tokens_extracted_from_usage_prompt_tokens_details():
    from types import SimpleNamespace
    record = record_model_call_start(
        call_id="s5_007_005",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
    )
    usage = SimpleNamespace(
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        prompt_tokens_details=SimpleNamespace(cached_tokens=60),
    )
    record_model_call_end(record, success=True, response_usage=usage)
    assert record.cached_tokens == 60


def test_cached_tokens_zero_when_no_cache_hit():
    from types import SimpleNamespace
    record = record_model_call_start(
        call_id="s5_007_006",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
    )
    usage = SimpleNamespace(
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        prompt_tokens_details=SimpleNamespace(cached_tokens=0),
    )
    record_model_call_end(record, success=True, response_usage=usage)
    assert record.cached_tokens == 0


def test_cached_tokens_none_when_usage_has_no_details():
    from types import SimpleNamespace
    record = record_model_call_start(
        call_id="s5_007_007",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
    )
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    record_model_call_end(record, success=True, response_usage=usage)
    assert record.cached_tokens is None


def test_preloaded_cached_tokens_not_overwritten_by_usage():
    from types import SimpleNamespace
    record = record_model_call_start(
        call_id="s5_007_008",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        cached_tokens=99,
    )
    usage = SimpleNamespace(
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        prompt_tokens_details=SimpleNamespace(cached_tokens=25),
    )
    record_model_call_end(record, success=True, response_usage=usage)
    # pre-loaded value (99) must NOT be overwritten by provider response (25)
    assert record.cached_tokens == 99


def test_existing_token_buckets_unchanged():
    record = record_model_call_start(
        call_id="s5_007_009",
        purpose="main_orchestrator",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an agent. " * 20},
            {"role": "user", "content": "Click the button."},
        ],
        tools=None,
        skill_tokens=450,
        # new fields provided
        prompt_pack_id="test_pack",
        model_class="main",
    )
    # Existing fields must be unaffected
    assert record.system_prompt_tokens is not None and record.system_prompt_tokens > 0
    assert record.skill_tokens == 450
    assert record.message_history_tokens is not None and record.message_history_tokens > 0
    # New fields set correctly
    assert record.prompt_pack_id == "test_pack"
    assert record.model_class == "main"
