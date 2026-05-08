from __future__ import annotations

import json
from pathlib import Path

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
    assert report["top_token_source"] in ("skill", "history", "dom_tool_result", "system")


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
