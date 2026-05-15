from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from runtime.token_report import build_token_report, parse_telemetry_line, parse_telemetry_lines
from tests.test_llm_runtime_controller_contract import (
    FakeCallRecorder,
    FakeTelemetrySink,
    _controller_dependencies,
    _load_controller_contract,
    _resolve_controller_target,
)
from tests.test_planning_through_controller_fake_model import (
    _install_common_run_stubs,
    _make_agent_loop,
    _make_current_step,
)


class _RaisingOpenAIClient:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **payload: Any) -> Any:
        self.calls.append(dict(payload))
        raise self._exc


class _NoneReturningOpenAIClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **payload: Any) -> Any:
        self.calls.append(dict(payload))
        return None


FAILED_TELEMETRY_LINE = (
    "[LLM_TELEMETRY] timestamp=2026-05-11T07:22:14.587Z call_id=llm_001 "
    "purpose=step_plan_normalizer model=gpt-4o-mini message_count=3 "
    "estimated_message_tokens=1998 estimated_tools_tokens=584 "
    "estimated_total_input_tokens=2582 skill_count=3 tool_count=6 "
    "success=false system_prompt_tokens=1748 skill_tokens=1699 "
    "tool_schema_tokens=584 message_history_tokens=238 dom_or_tool_result_tokens=0 "
    "prompt_pack_id=step_plan_normalizer.v1 prompt_pack_version=1 "
    "model_class=main context_bucket=planning "
    "skills_loaded=core,actions,download "
    "skill_levels=skill_summary,skill_summary,skill_summary "
    "prefix_hash=657eb55c3207eee9 latency_ms=2682 error_type=RuntimeError "
    "error_message=\"step_plan_normalizer controller did not return raw_response: MODEL_CALL_FAILED | upstream exploded\""
)


def _make_controller() -> tuple[Any, FakeTelemetrySink]:
    contract = _load_controller_contract()
    recorder = FakeCallRecorder()
    telemetry_sink = FakeTelemetrySink()
    dependencies = _controller_dependencies(recorder, contract.registry)
    dependencies["telemetry"] = telemetry_sink
    dependencies["telemetry_sink"] = telemetry_sink
    controller = _resolve_controller_target(contract.target, dependencies)
    return controller, telemetry_sink


def test_step_plan_normalizer_call_with_raw_response_returns_failure_result_when_model_client_raises() -> None:
    controller, telemetry_sink = _make_controller()
    call = getattr(controller, "call_with_raw_response", None)
    assert callable(call)

    client = _RaisingOpenAIClient(RuntimeError("upstream exploded"))
    result = asyncio.run(
        call(
            purpose="step_plan_normalizer",
            messages=[{"role": "user", "content": "Plan the next step"}],
            phase="planning",
            context_mode="compact",
            tools=[
                {"type": "function", "function": {"name": "send_to_overlay"}},
                {"type": "function", "function": {"name": "ask_user"}},
                {"type": "function", "function": {"name": "dom_extract"}},
            ],
            tool_choice="auto",
            client=client,
        )
    )

    assert result["raw_response"] is None
    assert result["raw_message"] is None
    assert result["tool_calls"] == []
    assert result["validation_status"] == "retry_failed"
    assert result["error_code"] == "MODEL_CALL_FAILED"
    assert "upstream exploded" in str(result.get("message") or "")
    assert result["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert result["prefix_hash"]
    assert len(str(result["prefix_hash"])) == 16
    assert result["skills_loaded"]
    assert result["skill_levels"]
    assert client.calls
    assert telemetry_sink.records
    telemetry_record = telemetry_sink.records[-1]
    assert telemetry_record["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert telemetry_record["prefix_hash"] == result["prefix_hash"]
    assert telemetry_record["skills_loaded"]
    assert telemetry_record["skill_levels"]


def test_step_plan_normalizer_call_with_raw_response_returns_failure_result_when_model_client_returns_none() -> None:
    controller, telemetry_sink = _make_controller()
    call = getattr(controller, "call_with_raw_response", None)
    assert callable(call)

    client = _NoneReturningOpenAIClient()
    result = asyncio.run(
        call(
            purpose="step_plan_normalizer",
            messages=[{"role": "user", "content": "Plan the next step"}],
            phase="planning",
            context_mode="compact",
            tools=[
                {"type": "function", "function": {"name": "send_to_overlay"}},
                {"type": "function", "function": {"name": "ask_user"}},
                {"type": "function", "function": {"name": "dom_extract"}},
            ],
            tool_choice="auto",
            client=client,
        )
    )

    assert result["raw_response"] is None
    assert result["raw_message"] is None
    assert result["tool_calls"] == []
    assert result["validation_status"] == "invalid"
    assert result["error_code"] == "EMPTY_MODEL_RESPONSE"
    assert "no response" in str(result.get("message") or "").lower()
    assert result["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert len(str(result["prefix_hash"])) == 16
    assert telemetry_sink.records
    telemetry_record = telemetry_sink.records[-1]
    assert telemetry_record["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert telemetry_record["prefix_hash"] == result["prefix_hash"]


def test_agent_step_plan_normalizer_reports_controller_error_details_and_preserves_prompt_pack_metadata(capsys) -> None:
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict[str, Any]]] = []
    _install_common_run_stubs(loop, sent_messages)
    loop.current_steps = [_make_current_step()]

    async def fake_controller_call(**kwargs: Any) -> dict[str, Any]:
        return {
            "used_controller": True,
            "validation_status": "retry_failed",
            "error_code": "MODEL_CALL_FAILED",
            "message": "upstream exploded",
            "raw_response": None,
            "raw_message": None,
            "content": None,
            "tool_calls": [],
            "prompt_pack_applied": True,
            "prompt_pack_id": "step_plan_normalizer.v1",
            "prompt_pack_version": 1,
            "prefix_hash": "deadbeefdeadbeef",
            "system_prompt_tokens": 321,
            "estimated_message_tokens": 654,
            "estimated_input_tokens": 789,
        }

    loop._llm_runtime_controller = SimpleNamespace(call_with_raw_response=fake_controller_call)

    asyncio.run(loop.run([_make_current_step()]))

    stdout = capsys.readouterr().out
    assert "prompt_pack_id=step_plan_normalizer.v1" in stdout
    assert "prefix_hash=deadbeefdeadbeef" in stdout
    assert "skill_levels=" in stdout
    assert "MODEL_CALL_FAILED" in stdout or "upstream exploded" in stdout
    assert any(message_type == "error" for message_type, _payload in sent_messages)
    error_messages = [
        str(payload.get("message") or "")
        for message_type, payload in sent_messages
        if message_type == "error"
    ]
    assert any("MODEL_CALL_FAILED" in message or "upstream exploded" in message for message in error_messages)
    assert all(
        message_type not in {"plan_ready", "step_recorded", "code_update", "run_completed"}
        for message_type, _payload in sent_messages
    )


def test_failed_telemetry_line_round_trips_prompt_pack_and_prefix_hash() -> None:
    record = parse_telemetry_line(FAILED_TELEMETRY_LINE)
    assert record is not None
    assert record["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert record["prefix_hash"] == "657eb55c3207eee9"

    report = build_token_report(parse_telemetry_lines(FAILED_TELEMETRY_LINE), test_name="paid_retry_blocker")
    assert report["prompt_pack_ids"] == ["step_plan_normalizer.v1"]
    assert report["skills_loaded"] == ["core", "actions", "download"]
    assert report["skill_levels"] == ["skill_summary"]
    assert report["total_cached_tokens"] == 0
