from __future__ import annotations

from runtime.llm_runtime_controller import PURPOSE_REGISTRY
from runtime.token_report import build_token_report, parse_telemetry_line, parse_telemetry_lines


PAID_ARTIFACT_TELEMETRY_LINE = (
    "[LLM_TELEMETRY] timestamp=2026-05-11T06:21:14.245Z call_id=llm_001 "
    "purpose=step_plan_normalizer model=gpt-4o-mini message_count=3 "
    "estimated_message_tokens=1095 estimated_tools_tokens=584 "
    "estimated_total_input_tokens=2636 skill_count=3 tool_count=6 "
    "success=false system_prompt_tokens=840 skill_tokens=1699 "
    "tool_schema_tokens=584 message_history_tokens=238 "
    "dom_or_tool_result_tokens=0 prompt_pack_id=step_plan_normalizer.v1 "
    "prompt_pack_version=1 model_class=main context_bucket=planning "
    "skills_loaded=core,actions,download prefix_hash=657eb55c3207eee9 "
    "latency_ms=0 error_type=RuntimeError "
    "error_message=\"step_plan_normalizer controller did not return raw_response\""
)


def test_step_plan_normalizer_budget_covers_paid_artifact_tokens() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    assert policy["token_budget"] >= 2636
    assert policy["token_budget"] <= 3000


def test_parse_telemetry_line_preserves_digit_prefixed_prefix_hash_and_timestamp() -> None:
    record = parse_telemetry_line(PAID_ARTIFACT_TELEMETRY_LINE)

    assert record is not None
    assert record["timestamp"] == "2026-05-11T06:21:14.245Z"
    assert record["prefix_hash"] == "657eb55c3207eee9"


def test_token_report_includes_skill_levels_when_emitted() -> None:
    line = (
        PAID_ARTIFACT_TELEMETRY_LINE
        + " skill_levels=core_compact,core_compact,skill_summary"
    )
    report = build_token_report(parse_telemetry_lines(line), test_name="paid_blocker")

    assert report["skills_loaded"] == ["core", "actions", "download"]
    assert report["skill_levels"] == ["core_compact", "skill_summary"]
    assert report["prompt_pack_ids"] == ["step_plan_normalizer.v1"]

