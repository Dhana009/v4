from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.token_report import (
    parse_telemetry_line,
    parse_telemetry_lines,
    build_token_report,
    write_token_report,
    WARN_CALLS_PER_TEST,
    WARN_INPUT_TOKENS_PER_TEST,
)


_SAMPLE_LINE = (
    "[LLM_TELEMETRY] timestamp=2026-05-08T12:00:00.000Z call_id=llm_001 "
    "purpose=main_orchestrator model=gpt-4o-mini message_count=5 "
    "estimated_message_tokens=1200 estimated_tools_tokens=300 "
    "estimated_total_input_tokens=1500 skill_count=2 tool_count=6 "
    "success=true system_prompt_tokens=400 skill_tokens=350 "
    "tool_schema_tokens=300 message_history_tokens=450 "
    "dom_or_tool_result_tokens=50 output_tokens=180 latency_ms=1240"
)

_SAMPLE_LINE_2 = (
    "[LLM_TELEMETRY] timestamp=2026-05-08T12:00:05.000Z call_id=llm_002 "
    "purpose=main_orchestrator model=gpt-4o-mini message_count=8 "
    "estimated_message_tokens=2100 estimated_tools_tokens=300 "
    "estimated_total_input_tokens=2400 skill_count=2 tool_count=6 "
    "success=true system_prompt_tokens=400 skill_tokens=350 "
    "tool_schema_tokens=300 message_history_tokens=1350 "
    "dom_or_tool_result_tokens=50 output_tokens=200 latency_ms=1500"
)


def test_parse_telemetry_line_returns_dict():
    record = parse_telemetry_line(_SAMPLE_LINE)
    assert record is not None
    assert record["call_id"] == "llm_001"
    assert record["purpose"] == "main_orchestrator"
    assert record["estimated_total_input_tokens"] == 1500


def test_parse_telemetry_line_includes_breakdown_fields():
    record = parse_telemetry_line(_SAMPLE_LINE)
    assert record["system_prompt_tokens"] == 400
    assert record["skill_tokens"] == 350
    assert record["tool_schema_tokens"] == 300
    assert record["message_history_tokens"] == 450
    assert record["dom_or_tool_result_tokens"] == 50


def test_parse_telemetry_line_returns_none_for_non_telemetry():
    assert parse_telemetry_line("some random log line") is None
    assert parse_telemetry_line("[CONTEXT_MANAGER] purpose=main") is None
    assert parse_telemetry_line("") is None


def test_parse_telemetry_lines_extracts_all():
    log_text = f"some preamble\n{_SAMPLE_LINE}\nother log\n{_SAMPLE_LINE_2}\n"
    records = parse_telemetry_lines(log_text)
    assert len(records) == 2
    assert records[0]["call_id"] == "llm_001"
    assert records[1]["call_id"] == "llm_002"


def test_build_token_report_call_count():
    records = parse_telemetry_lines(f"{_SAMPLE_LINE}\n{_SAMPLE_LINE_2}")
    report = build_token_report(records, test_name="test_basic_click")
    assert report["call_count"] == 2
    assert report["test_name"] == "test_basic_click"


def test_build_token_report_total_input_tokens():
    records = parse_telemetry_lines(f"{_SAMPLE_LINE}\n{_SAMPLE_LINE_2}")
    report = build_token_report(records, test_name="test_basic_click")
    assert report["total_estimated_input_tokens"] == 1500 + 2400


def test_build_token_report_largest_call():
    records = parse_telemetry_lines(f"{_SAMPLE_LINE}\n{_SAMPLE_LINE_2}")
    report = build_token_report(records, test_name="test_basic_click")
    assert report["largest_call_id"] == "llm_002"
    assert report["largest_call_tokens"] == 2400


def test_build_token_report_top_token_source():
    records = parse_telemetry_lines(f"{_SAMPLE_LINE}\n{_SAMPLE_LINE_2}")
    report = build_token_report(records, test_name="test_basic_click")
    assert report["top_token_source"] == "history"


@pytest.mark.parametrize(
    ("replacement", "expected_source"),
    [
        ("system_prompt_tokens=400", "system"),
        ("skill_tokens=350", "skill"),
        ("tool_schema_tokens=300", "tool_schema"),
        ("message_history_tokens=450", "history"),
        ("dom_or_tool_result_tokens=50", "dom_tool_result"),
    ],
)
def test_build_token_report_selects_largest_token_bucket(replacement: str, expected_source: str):
    boosted_line = _SAMPLE_LINE.replace(replacement, f"{replacement.split('=')[0]}=1200")
    records = parse_telemetry_lines(boosted_line)
    report = build_token_report(records, test_name="bucket_test")
    assert report["top_token_source"] == expected_source


def test_build_token_report_warns_on_high_call_count():
    line = _SAMPLE_LINE
    many_lines = "\n".join(line.replace("llm_001", f"llm_{i:03d}") for i in range(WARN_CALLS_PER_TEST + 2))
    records = parse_telemetry_lines(many_lines)
    report = build_token_report(records, test_name="heavy_test")
    assert any("call_count" in w for w in report["warnings"])


def test_build_token_report_warns_on_high_tokens():
    big_line = _SAMPLE_LINE.replace("estimated_total_input_tokens=1500", f"estimated_total_input_tokens={WARN_INPUT_TOKENS_PER_TEST + 1}")
    records = parse_telemetry_lines(big_line)
    report = build_token_report(records, test_name="expensive_test")
    assert any("estimated_input_tokens" in w for w in report["warnings"])


def test_build_token_report_handles_empty_records():
    report = build_token_report([], test_name="empty_test")
    assert report["call_count"] == 0
    assert report["total_estimated_input_tokens"] == 0
    assert report["warnings"] == []


def test_build_token_report_handles_missing_fields():
    # Record with no breakdown fields — must not crash
    minimal_line = "[LLM_TELEMETRY] call_id=llm_001 purpose=main estimated_total_input_tokens=500 success=true"
    records = parse_telemetry_lines(minimal_line)
    report = build_token_report(records, test_name="minimal_test")
    assert report["call_count"] == 1
    assert report["total_estimated_input_tokens"] == 500
    assert report["top_token_source"] == "system"
    assert report["token_breakdown"]["tool_schema"] == 0


def test_build_token_report_includes_tool_schema_totals():
    records = parse_telemetry_lines(f"{_SAMPLE_LINE}\n{_SAMPLE_LINE_2}")
    report = build_token_report(records, test_name="totals_test")
    assert report["token_breakdown"]["tool_schema"] == 600
    assert report["token_breakdown"]["system"] == 800
    assert report["token_breakdown"]["skill"] == 700


def test_write_token_report_creates_file(tmp_path: Path):
    records = parse_telemetry_lines(_SAMPLE_LINE)
    report = build_token_report(records, test_name="test_write")
    path = write_token_report(tmp_path, report)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["test_name"] == "test_write"
    assert data["call_count"] == 1


def test_write_token_report_valid_json(tmp_path: Path):
    report = build_token_report([], test_name="empty")
    path = write_token_report(tmp_path, report)
    parsed = json.loads(path.read_text())
    assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# S5-007: new attribution fields in token report
# ---------------------------------------------------------------------------

_S5_LINE_WITH_ATTRIBUTION = (
    "[LLM_TELEMETRY] timestamp=2026-05-10T00:00:00.000Z call_id=llm_s5_001 "
    "purpose=step_plan_normalizer model=gpt-4o-mini message_count=3 "
    "estimated_message_tokens=800 estimated_tools_tokens=120 "
    "estimated_total_input_tokens=920 skill_count=2 tool_count=3 "
    "success=true system_prompt_tokens=350 skill_tokens=280 "
    "tool_schema_tokens=120 message_history_tokens=170 "
    "dom_or_tool_result_tokens=0 output_tokens=45 latency_ms=800 "
    "prompt_pack_id=planning_pack_v1 model_class=main context_bucket=planning "
    "cached_tokens=40 skills_loaded=llm_runtime_controller,prompt_persona_skill_loading "
    "skill_levels=core_compact,core_compact"
)


def test_token_report_includes_prompt_pack_ids():
    records = parse_telemetry_lines(_S5_LINE_WITH_ATTRIBUTION)
    report = build_token_report(records, test_name="s5_attribution")
    assert "prompt_pack_ids" in report
    assert "planning_pack_v1" in report["prompt_pack_ids"]


def test_token_report_includes_model_classes():
    records = parse_telemetry_lines(_S5_LINE_WITH_ATTRIBUTION)
    report = build_token_report(records, test_name="s5_attribution")
    assert "model_classes" in report
    assert "main" in report["model_classes"]


def test_token_report_includes_context_buckets():
    records = parse_telemetry_lines(_S5_LINE_WITH_ATTRIBUTION)
    report = build_token_report(records, test_name="s5_attribution")
    assert "context_buckets" in report
    assert "planning" in report["context_buckets"]


def test_token_report_includes_total_cached_tokens():
    records = parse_telemetry_lines(_S5_LINE_WITH_ATTRIBUTION)
    report = build_token_report(records, test_name="s5_attribution")
    assert "total_cached_tokens" in report
    assert report["total_cached_tokens"] == 40


def test_token_report_cached_tokens_aggregates_across_calls():
    line1 = _S5_LINE_WITH_ATTRIBUTION  # cached_tokens=40
    line2 = _S5_LINE_WITH_ATTRIBUTION.replace("llm_s5_001", "llm_s5_002").replace("cached_tokens=40", "cached_tokens=60")
    records = parse_telemetry_lines(f"{line1}\n{line2}")
    report = build_token_report(records, test_name="cache_aggregate")
    assert report["total_cached_tokens"] == 100


def test_token_report_empty_attribution_fields_when_missing():
    # Old-style line without S5-007 fields
    records = parse_telemetry_lines(_SAMPLE_LINE)
    report = build_token_report(records, test_name="old_style")
    assert report["prompt_pack_ids"] == []
    assert report["model_classes"] == []
    assert report["context_buckets"] == []
    assert report["total_cached_tokens"] == 0


def test_token_report_skills_loaded_from_s5_line():
    records = parse_telemetry_lines(_S5_LINE_WITH_ATTRIBUTION)
    report = build_token_report(records, test_name="skills")
    assert "llm_runtime_controller" in report["skills_loaded"]
    assert "prompt_persona_skill_loading" in report["skills_loaded"]
    assert report["skill_levels"] == ["core_compact"]


def test_old_token_report_fields_still_present():
    records = parse_telemetry_lines(_S5_LINE_WITH_ATTRIBUTION)
    report = build_token_report(records, test_name="backward_compat")
    # All original fields must still be present
    assert "call_count" in report
    assert "total_estimated_input_tokens" in report
    assert "total_output_tokens" in report
    assert "top_token_source" in report
    assert "token_breakdown" in report
    assert "skills_loaded" in report
    assert "purposes" in report
    assert "warnings" in report
    assert "records" in report


def test_token_report_deduplicates_prompt_pack_ids():
    line1 = _S5_LINE_WITH_ATTRIBUTION
    line2 = _S5_LINE_WITH_ATTRIBUTION.replace("llm_s5_001", "llm_s5_002")
    records = parse_telemetry_lines(f"{line1}\n{line2}")
    report = build_token_report(records, test_name="dedup")
    # Same pack id on both lines → should appear once
    assert report["prompt_pack_ids"].count("planning_pack_v1") == 1


def test_empty_report_has_attribution_fields():
    report = build_token_report([], test_name="empty_s5")
    assert report["prompt_pack_ids"] == []
    assert report["model_classes"] == []
    assert report["context_buckets"] == []
    assert report["total_cached_tokens"] == 0
