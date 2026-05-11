from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

from runtime.correction_context import (
    build_plan_diff_editor_context_payload,
    correction_needs_locator_context,
    render_plan_diff_editor_context,
)
from runtime.llm_runtime_controller import LLMRuntimeController, PURPOSE_REGISTRY
from runtime.prompt_pack_builder import (
    NON_NEGOTIABLE_RUNTIME_RULES,
    REGISTERED_PROMPT_PACK_PURPOSES,
    build_plan_diff_editor_pack,
    build_recovery_diagnoser_pack,
    build_step_plan_normalizer_pack,
)
from runtime.prompt_packs import hash_stable_prefix
from runtime.recovery_context import (
    build_recovery_diagnoser_context_payload,
    render_recovery_diagnoser_context,
)
from runtime.skill_policy import COMPACT_ONLY_PURPOSES, can_escalate_to_full_skills
from runtime.skill_selector import select_skills_for_purpose
from runtime.telemetry import _format_telemetry_line, record_model_call_end, record_model_call_start
from runtime.token_report import build_token_report, parse_telemetry_line
from runtime.tool_schema_policy import planning_tools_for_purpose, recovery_tools_for_purpose


class FakeTelemetrySink:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def record(self, **payload: Any) -> None:
        self.records.append(dict(payload))


class JsonSchemaValidator:
    def validate(self, **payload: Any) -> dict[str, Any]:
        raw_output = payload.get("raw_output")
        parsed_output = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
        return {
            "ok": True,
            "validation_status": "valid",
            "errors": [],
            "parsed_output": parsed_output,
        }


class FakeClient:
    def __init__(self, response: Any) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = response
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create),
        )

    async def _create(self, **payload: Any) -> Any:
        self.calls.append(dict(payload))
        return self._response


def _response(
    content: str | None,
    *,
    tool_calls: list[Any] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=list(tool_calls or []),
                    role="assistant",
                )
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            prompt_tokens_details=SimpleNamespace(cached_tokens=13),
        ),
    )


def _controller_for(response: Any, telemetry_sink: FakeTelemetrySink | None = None) -> tuple[LLMRuntimeController, FakeClient, FakeTelemetrySink]:
    sink = telemetry_sink or FakeTelemetrySink()
    client = FakeClient(response)
    controller = LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=JsonSchemaValidator(),
        telemetry_sink=sink,
        model_client=client,
    )
    return controller, client, sink


def _tool(name: str) -> dict[str, object]:
    return {"type": "function", "function": {"name": name}}


def _user_message(content: str) -> dict[str, str]:
    return {"role": "user", "content": content}


def test_every_registered_prompt_pack_contains_non_negotiable_safety_rules() -> None:
    for purpose in REGISTERED_PROMPT_PACK_PURPOSES:
        pack = build_step_plan_normalizer_pack() if purpose == "step_plan_normalizer" else (
            build_plan_diff_editor_pack() if purpose == "plan_diff_editor" else build_recovery_diagnoser_pack()
        )
        for rule in NON_NEGOTIABLE_RUNTIME_RULES:
            assert rule in pack.stable_prefix


def test_registered_prompt_packs_do_not_use_forbidden_finality_phrases() -> None:
    forbidden_phrases = (
        "mark the step completed",
        "record the step",
        "execute before confirmation",
        "frontend should update lifecycle",
    )
    for purpose in REGISTERED_PROMPT_PACK_PURPOSES:
        pack = build_step_plan_normalizer_pack() if purpose == "step_plan_normalizer" else (
            build_plan_diff_editor_pack() if purpose == "plan_diff_editor" else build_recovery_diagnoser_pack()
        )
        stable_prefix = pack.stable_prefix.lower()
        for phrase in forbidden_phrases:
            assert phrase not in stable_prefix


def test_step_plan_normalizer_pack_is_proposal_only_and_does_not_claim_validation_truth() -> None:
    pack = build_step_plan_normalizer_pack()
    stable_prefix = pack.stable_prefix

    assert "You reason and propose only" in stable_prefix
    assert "Backend Step Runner owns lifecycle truth." in stable_prefix
    assert "Do not claim a locator, action, assertion, or result is validated." in stable_prefix


def test_plan_diff_editor_pack_keeps_no_silent_drop_reorder_split_merge_policy() -> None:
    pack = build_plan_diff_editor_pack()
    stable_prefix = pack.stable_prefix.lower()

    assert "do not silently drop operations" in stable_prefix
    assert "do not silently reorder operations" in stable_prefix
    assert "do not split or merge parent steps unless the user explicitly asks" in stable_prefix
    assert "backend validates and applies the diff" in stable_prefix


def test_recovery_diagnoser_pack_stays_anchored_and_never_claims_recovered() -> None:
    pack = build_recovery_diagnoser_pack()
    stable_prefix = pack.stable_prefix.lower()

    assert "stay anchored to the failed step" in stable_prefix
    assert "diagnose the failed step only" in stable_prefix
    assert "do not mark the step recovered, recorded, skipped, failed, or completed" in stable_prefix


def test_plan_diff_editor_has_zero_tools() -> None:
    assert planning_tools_for_purpose("plan_diff_editor") == ()


def test_recovery_diagnoser_has_only_browser_get_state_and_ask_user() -> None:
    assert recovery_tools_for_purpose("recovery_diagnoser") == ("browser_get_state", "ask_user")


def test_replay_repair_specialist_has_only_browser_get_state_and_ask_user() -> None:
    assert recovery_tools_for_purpose("replay_repair_specialist") == ("browser_get_state", "ask_user")


def test_page_intelligence_summarizer_has_only_dom_extract() -> None:
    assert planning_tools_for_purpose("page_intelligence_summarizer") == ("dom_extract",)


def test_codegen_review_unknown_purpose_has_zero_tools() -> None:
    assert planning_tools_for_purpose("codegen_review") == ()
    assert recovery_tools_for_purpose("codegen_review") == ()


def test_unknown_purpose_returns_empty_minimal_tools_not_all_tools() -> None:
    assert planning_tools_for_purpose("unknown_future_purpose") == ()
    assert recovery_tools_for_purpose("unknown_future_purpose") == ()


def test_step_plan_normalizer_does_not_receive_unrelated_high_risk_tools() -> None:
    planning_tools = planning_tools_for_purpose("step_plan_normalizer")
    forbidden = {"action_click", "action_fill", "action_assert"}

    assert not forbidden.intersection(planning_tools)
    assert {"send_to_overlay", "browser_get_state", "dom_extract"}.intersection(planning_tools)


def test_compact_only_purposes_cannot_load_full_skills_by_default() -> None:
    for purpose in COMPACT_ONLY_PURPOSES:
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        selection = select_skills_for_purpose(purpose, policy=policy)
        assert selection.preserve_full_prompt is False
        assert "full_skill" not in selection.skill_levels


def test_unknown_purpose_gets_minimal_compact_core_guidance() -> None:
    selection = select_skills_for_purpose("unknown_future_purpose", policy=None)

    assert selection.preserve_full_prompt is False
    assert selection.loaded_skill_names == ["llm_runtime_controller"]
    assert selection.skill_levels == ["core_compact"]


def test_recovery_debug_purpose_gets_compact_debug_guidance_not_full_dump_by_default() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("recovery_diagnoser")
    selection = select_skills_for_purpose("recovery_diagnoser", policy=policy)

    assert selection.preserve_full_prompt is False
    assert selection.loaded_skill_names == [
        "llm_runtime_controller",
        "prompt_persona_skill_loading",
        "observability_trace",
        "memory_human_feedback",
    ]
    assert selection.skill_levels == [
        "core_compact",
        "core_compact",
        "debug_skill",
        "debug_skill",
    ]


def test_plan_diff_editor_remains_compact_only_on_retry_or_escalation() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("plan_diff_editor")
    selection = select_skills_for_purpose(
        "plan_diff_editor",
        policy=policy,
        escalation_reason="schema_retry",
    )

    assert selection.preserve_full_prompt is False
    assert selection.loaded_skill_names == [
        "llm_runtime_controller",
        "prompt_persona_skill_loading",
    ]


def test_full_skill_escalation_requires_explicit_reason_and_allowed_purpose() -> None:
    assert can_escalate_to_full_skills("step_plan_normalizer", escalation_reason="schema_retry") is True
    assert can_escalate_to_full_skills("step_plan_normalizer") is False
    assert can_escalate_to_full_skills("step_plan_normalizer", escalation_reason="not_allowed") is False
    assert can_escalate_to_full_skills("plan_diff_editor", escalation_reason="schema_retry") is False


def test_correction_context_excludes_full_dom_and_unrelated_history_by_default() -> None:
    payload = build_plan_diff_editor_context_payload(
        active_plan_state={
            "plan_id": "plan-1",
            "full_dom": "<html><body>raw full dom</body></html>",
            "steps": [
                {
                    "step_id": "step-1",
                    "intent": "Click the Get started button",
                    "children": [
                        {
                            "operation_id": "op-1",
                            "type": "click",
                            "target": "Get started",
                        }
                    ],
                }
            ],
        },
        correction_state={
            "target_step_id": "step-1",
            "correction_text": "add visible assertion first",
            "browser_history": "old history that should not leak",
            "tool_output": "raw tool output",
        },
        validation_feedback="validation feedback message",
        allowed_edit_policy="preserve existing child operations",
    )
    rendered = render_plan_diff_editor_context(payload)

    assert "<html" not in rendered.lower()
    assert "raw tool output" not in rendered
    assert "old history" not in rendered
    assert "validation feedback message" in rendered
    assert payload["locator_context_required"] == "no"


def test_recovery_context_includes_retry_attempts_only_for_current_failed_step() -> None:
    payload = build_recovery_diagnoser_context_payload(
        run_id="run-1",
        failed_step_state={
            "step_id": "step-1",
            "operation_id": "op-1",
            "last_error": "timeout while clicking",
        },
        failed_step_id="step-1",
        failed_operation_id="op-1",
        error_summary="timeout while clicking",
        current_page="http://example.test/current | Fixture page",
        retry_attempts=[
            {"failed_step_id": "step-1", "status": "retrying", "summary": "retry with visibility check"},
            {"failed_step_id": "step-2", "status": "retrying", "summary": "ignore this old failure"},
        ],
        messages=[
            {"role": "tool", "content": "<html><body>raw full dom</body></html>"},
            {"role": "assistant", "content": "Recovery: retry after checking visibility."},
        ],
    )
    rendered = render_recovery_diagnoser_context(payload)

    assert "DYNAMIC_RECOVERY_CONTEXT:" in rendered
    assert "raw full dom" not in rendered
    assert "step_id=step-1" in rendered or "step-1" in rendered
    assert "step-2" not in rendered
    assert "timeout while clicking" in rendered


def test_locator_sensitive_correction_is_flagged_rather_than_injecting_full_dom() -> None:
    payload = build_plan_diff_editor_context_payload(
        active_plan_state={
            "plan_id": "plan-1",
            "steps": [
                {
                    "step_id": "step-1",
                    "intent": "Click the Get started button",
                    "children": [
                        {
                            "operation_id": "op-1",
                            "type": "click",
                            "target": "Get started",
                            "locator": 'get_by_text("Get started", exact=True)',
                        }
                    ],
                }
            ],
        },
        correction_state={
            "target_step_id": "step-1",
            "correction_text": "change the locator for the button",
            "explicit_target_change": True,
        },
        validation_feedback="locator mismatch",
        allowed_edit_policy="preserve existing child operations",
    )
    rendered = render_plan_diff_editor_context(payload)

    assert correction_needs_locator_context("change the locator for the button")
    assert payload["locator_context_required"] == "yes"
    assert "<html" not in rendered.lower()


def test_controller_step_plan_normalizer_emits_prompt_pack_metadata() -> None:
    telemetry_sink = FakeTelemetrySink()
    controller, client, _ = _controller_for(
        _response('{"purpose":"step_plan_normalizer","schema_id":"step_plan_normalizer.v1"}'),
        telemetry_sink=telemetry_sink,
    )

    result = asyncio.run(
        controller.call(
            purpose="step_plan_normalizer",
            messages=[_user_message("click the green primary CTA")],
            phase="planning",
            context_mode="compact",
            tools=[
                _tool("send_to_overlay"),
                _tool("action_click"),
                _tool("ask_user"),
            ],
        )
    )

    expected_prefix_hash = hash_stable_prefix(build_step_plan_normalizer_pack().stable_prefix)

    assert result["prompt_pack_applied"] is True
    assert result["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert result["prefix_hash"] == expected_prefix_hash
    assert telemetry_sink.records
    assert telemetry_sink.records[-1]["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert telemetry_sink.records[-1]["prefix_hash"] == expected_prefix_hash
    assert telemetry_sink.records[-1]["skills_loaded"] == [
        "llm_runtime_controller",
        "prompt_persona_skill_loading",
    ]
    assert client.calls
    tool_names = [tool["function"]["name"] for tool in client.calls[-1]["tools"] or []]
    assert "action_click" not in tool_names
    assert "send_to_overlay" in tool_names


def test_model_call_telemetry_accepts_skills_levels_and_cached_tokens() -> None:
    record = record_model_call_start(
        call_id="call-1",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan"}],
        tools=None,
        prompt_pack_id="step_plan_normalizer.v1",
        prompt_pack_version=1,
        skills_loaded=["llm_runtime_controller", "prompt_persona_skill_loading"],
        skill_levels=["core_compact", "core_compact"],
        model_class="main",
        context_bucket="planning",
        cached_tokens=13,
        prefix_hash="deadbeefdeadbeef",
    )

    assert record.prompt_pack_id == "step_plan_normalizer.v1"
    assert record.skills_loaded == ["llm_runtime_controller", "prompt_persona_skill_loading"]
    assert record.skill_levels == ["core_compact", "core_compact"]
    assert record.cached_tokens == 13
    assert record.prefix_hash == "deadbeefdeadbeef"


def test_model_call_telemetry_missing_optional_fields_stay_none() -> None:
    record = record_model_call_start(
        call_id="call-2",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan"}],
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


def test_token_report_includes_prompt_pack_and_cache_fields_when_present() -> None:
    record = record_model_call_start(
        call_id="call-3",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan"}],
        tools=None,
        prompt_pack_id="step_plan_normalizer.v1",
        prompt_pack_version=1,
        skills_loaded=["llm_runtime_controller"],
        skill_levels=["core_compact"],
        model_class="main",
        context_bucket="planning",
        cached_tokens=13,
        prefix_hash="deadbeefdeadbeef",
    )
    record_model_call_end(record, success=True)

    telemetry_line = _format_telemetry_line(record)
    parsed_line = parse_telemetry_line(telemetry_line)
    assert parsed_line is not None
    report = build_token_report([parsed_line])

    assert report["prompt_pack_ids"] == ["step_plan_normalizer.v1"]
    assert report["total_cached_tokens"] == 13
    assert report["model_classes"] == ["main"]
    assert report["context_buckets"] == ["planning"]
    assert report["skills_loaded"] == ["llm_runtime_controller"]
    assert report["skill_levels"] == ["core_compact"]


def test_controller_raw_response_preserves_tool_calls() -> None:
    telemetry_sink = FakeTelemetrySink()
    controller, client, _ = _controller_for(
        _response(
            None,
            tool_calls=[
                {
                    "id": "tool-1",
                    "function": {
                        "name": "send_to_overlay",
                        "arguments": "{\"message_type\":\"plan_ready\"}",
                    },
                }
            ],
        ),
        telemetry_sink=telemetry_sink,
    )

    result = asyncio.run(
        controller.call_with_raw_response(
            purpose="step_plan_normalizer",
            messages=[_user_message("click the green primary CTA")],
            phase="planning",
            context_mode="compact",
            tools=[_tool("send_to_overlay"), _tool("action_click"), _tool("ask_user")],
            tool_choice="auto",
        )
    )

    expected_prefix_hash = hash_stable_prefix(build_step_plan_normalizer_pack().stable_prefix)

    assert result["validation_status"] == "tool_calls_preserved"
    assert len(result["tool_calls"]) == 1
    assert result["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert result["prefix_hash"] == expected_prefix_hash
    assert telemetry_sink.records[-1]["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert telemetry_sink.records[-1]["prefix_hash"] == expected_prefix_hash
    assert client.calls
    tool_names = [tool["function"]["name"] for tool in client.calls[-1]["tools"] or []]
    assert "action_click" not in tool_names
    assert "send_to_overlay" in tool_names


def test_plan_diff_editor_content_only_path_remains_valid() -> None:
    telemetry_sink = FakeTelemetrySink()
    controller, client, _ = _controller_for(
        _response('{"purpose":"plan_diff_editor","schema_id":"plan_diff_editor.v1"}'),
        telemetry_sink=telemetry_sink,
    )

    result = asyncio.run(
        controller.call(
            purpose="plan_diff_editor",
            messages=[_user_message("Correction: add assertion first")],
            phase="planning",
            context_mode="compact",
            tools=[_tool("send_to_overlay"), _tool("action_click")],
        )
    )

    expected_prefix_hash = hash_stable_prefix(build_plan_diff_editor_pack().stable_prefix)

    assert result["validation_status"] == "valid"
    assert result["prompt_pack_id"] == "plan_diff_editor.v1"
    assert result["prefix_hash"] == expected_prefix_hash
    assert telemetry_sink.records[-1]["prompt_pack_id"] == "plan_diff_editor.v1"
    assert telemetry_sink.records[-1]["prefix_hash"] == expected_prefix_hash
    assert client.calls
    assert client.calls[-1]["tools"] in (None, [])
    assert client.calls[-1]["messages"][0]["content"].startswith("PROMPT_PACK_ID: plan_diff_editor.v1")


def test_malformed_response_cannot_look_like_success() -> None:
    controller, _, _ = _controller_for(
        _response(None, tool_calls=[]),
    )

    result = asyncio.run(
        controller.call_with_raw_response(
            purpose="step_plan_normalizer",
            messages=[_user_message("click the green primary CTA")],
            phase="planning",
            context_mode="compact",
            tools=[],
            tool_choice="auto",
        )
    )

    assert result["validation_status"] == "invalid"
    assert result["tool_calls"] == []
    assert result["content"] is None


# ---------------------------------------------------------------------------
# BUG-S5-013-007: Convergence contract guardrail regression tests
# ---------------------------------------------------------------------------

def test_prompt_pack_includes_terminal_output_requirement() -> None:
    """Stable prefix must contain TERMINAL_OUTPUT_REQUIREMENT section."""
    pack = build_step_plan_normalizer_pack()
    assert "TERMINAL_OUTPUT_REQUIREMENT" in pack.stable_prefix, (
        "TERMINAL_OUTPUT_REQUIREMENT section missing from step_plan_normalizer stable prefix"
    )


def test_prompt_pack_includes_ambiguity_rule() -> None:
    """Stable prefix must contain AMBIGUITY_RULE to guide the model on ambiguous pages."""
    pack = build_step_plan_normalizer_pack()
    assert "AMBIGUITY_RULE" in pack.stable_prefix, (
        "AMBIGUITY_RULE section missing from step_plan_normalizer stable prefix"
    )


def test_ask_user_and_plan_ready_terminal_clarity_present() -> None:
    """Tool schema text must make ask_user clearly terminal for ambiguous cases."""
    from llm.tool_definitions import ToolDefinitions
    stub_loop = SimpleNamespace()
    td = ToolDefinitions(loop=stub_loop)
    tools = td.build()

    ask_user_tool = next(
        (t for t in tools if t.get("function", {}).get("name") == "ask_user"),
        None,
    )
    assert ask_user_tool is not None, "ask_user tool must be defined"
    description = ask_user_tool["function"]["description"]
    assert any(word in description.lower() for word in ("ambiguous", "unclear", "multiple", "clarif")), (
        "ask_user description must reference ambiguous/unclear intent as its trigger"
    )


def test_llm_thinking_non_terminal_limited() -> None:
    """send_to_overlay description must state llm_thinking is non-terminal and limited."""
    from llm.tool_definitions import ToolDefinitions
    stub_loop = SimpleNamespace()
    td = ToolDefinitions(loop=stub_loop)
    tools = td.build()

    overlay_tool = next(
        (t for t in tools if t.get("function", {}).get("name") == "send_to_overlay"),
        None,
    )
    assert overlay_tool is not None, "send_to_overlay tool must be defined"
    description = overlay_tool["function"]["description"]
    assert any(phrase in description.lower() for phrase in ("at most once", "must follow", "once")), (
        "send_to_overlay description must state llm_thinking is limited/non-terminal"
    )


def test_content_only_not_accepted_as_planning_success() -> None:
    """A content-only LLM response (no tool calls) must NOT set terminal_reason
    in the planning loop guard — it is non-terminal and must count toward no-progress.
    """
    from runtime.planning_loop_guard import inspect_planning_response

    content_only = SimpleNamespace(
        content="The page shows three profile sections; it is ambiguous which to use.",
        tool_calls=[],
        role="assistant",
    )
    inspection = inspect_planning_response(content_only)
    assert inspection.terminal_reason is None, (
        f"Content-only planning response must not be terminal; "
        f"got terminal_reason={inspection.terminal_reason!r}"
    )
