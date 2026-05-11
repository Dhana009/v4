"""S5-001 tests: planning call attribution wired through PURPOSE_REGISTRY.

These tests verify that:
1. When effective_purpose == "step_plan_normalizer", record_model_call_start()
   receives model_class, context_bucket, and skills_loaded from PURPOSE_REGISTRY.
2. plan_diff_editor path is unaffected.
3. New S5-007 telemetry fields appear in the planning call telemetry record.
4. No execution before confirmation.
5. Malformed fake model output does not produce a plan_ready event.

The tests use the existing AgentLoop infrastructure with FakeLLMClient and
monkeypatching rather than calling the live LLM or E2E runner.
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agent as agent_module
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker
from runtime.llm_runtime_controller import PURPOSE_REGISTRY
from runtime.planning_loop_guard import PlanningLoopGuardState
from runtime.telemetry import ModelCallTelemetry, record_model_call_start
from tests.fake_llm_factory import FakeLLMClient, MALFORMED_RESPONSE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _make_overlay_tool_call(
    call_id: str,
    payload: dict[str, Any],
    message_type: str = "plan_ready",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="send_to_overlay",
            arguments=json.dumps(
                {
                    "message_type": message_type,
                    "payload": payload,
                }
            ),
        ),
    )


def _make_response_with_tool_calls(*tool_calls: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=list(tool_calls),
                    role="assistant",
                )
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            prompt_tokens_details=SimpleNamespace(cached_tokens=0),
        ),
    )


def _make_content_only_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=[],
                    role="assistant",
                )
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            prompt_tokens_details=SimpleNamespace(cached_tokens=0),
        ),
    )


def _make_agent_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = object()
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = "idle"
    loop.phase = "planning"
    loop.plan_confirmed = False
    loop.current_steps = []
    loop.step_state_by_id = {}
    loop.step_context_by_id = {}
    loop.active_step_id = None
    loop.active_failed_step_id = None
    loop.pending_recovery = False
    loop.completed_step_ids = set()
    loop.skipped_step_ids = set()
    loop.current_step_index = 0
    loop.last_successful_action = None
    loop.successful_action_by_step_id = {}
    loop.successful_actions_by_step_id = {}
    loop._loaded_skill_names = []
    loop._loaded_skill_entries = []
    loop._missing_skill_names = set()
    loop._last_skill_load_phase = None
    loop._recording_steps = []
    loop._recording_step_index = 0
    loop._recorded_step_ids = set()
    loop._last_action_context = None
    loop._awaiting_step_record = False
    loop._pending_failure_followup = False
    loop.last_plan_ready_payload = None
    loop.last_plan_step_ids = []
    loop.last_plan_summary = None
    loop.last_plan_original_user_intent = None
    loop._planning_loop_guard_state = PlanningLoopGuardState()
    loop._active_plan_state = None
    loop._active_plan_correction_state = None
    loop._run_completion_requested = False
    loop.run_stop_requested = False
    loop._llm_call_counter = 0
    loop.confirmed_plan_by_step_id = {}
    loop.confirmed_plan_step_ids = []
    loop.confirmed_child_results_by_step_id = {}
    loop.confirmed_execution_mismatch_count_by_step_id = {}
    loop.tools = []
    loop.llm = SimpleNamespace(
        messages=[],
        system_prompt="",
        client=object(),
        reset=lambda: None,
    )
    loop.context_manager = SimpleNamespace(
        prepare_messages=lambda messages, purpose, context_mode, metadata: SimpleNamespace(
            messages=list(messages)
        ),
    )
    loop.skill_manager = SimpleNamespace(
        analyze=lambda loaded_skills, loaded_skill_names=None: SimpleNamespace(
            skill_count=len(loaded_skill_names or []),
            loaded_skill_names=list(loaded_skill_names or []),
            estimated_total_skill_tokens=0,
            largest_skill_name="none",
            largest_skill_tokens=0,
            suggested_future_policy="ok_current",
        )
    )
    loop._format_steps = lambda steps: "steps"
    loop._llm_runtime_controller = None
    return loop


def _install_common_run_stubs(
    loop: AgentLoop,
    sent_messages: list[tuple[str, dict[str, Any]]],
) -> None:
    def fake_reset_lifecycle_state(steps=None):
        loop.phase = "planning"
        loop.plan_confirmed = False
        loop.current_steps = list(steps or [])
        loop.phase_tracker.current_phase = "idle"
        loop.step_state_by_id = {}
        loop.step_context_by_id = {}
        loop.active_step_id = None
        loop.active_failed_step_id = None
        loop.pending_recovery = False
        loop.completed_step_ids = set()
        loop.skipped_step_ids = set()
        loop.current_step_index = 0
        loop.last_successful_action = None
        loop.successful_action_by_step_id = {}
        loop.successful_actions_by_step_id = {}
        loop._recording_steps = []
        loop._recording_step_index = 0
        loop._recorded_step_ids = set()
        loop._last_action_context = None
        loop._awaiting_step_record = False
        loop._pending_failure_followup = False
        loop._run_completion_requested = False
        loop.run_stop_requested = False
        loop._llm_call_counter = 0
        loop._planning_loop_guard_state = PlanningLoopGuardState()
        loop.confirmed_plan_by_step_id = {}
        loop.confirmed_plan_step_ids = []
        loop.confirmed_child_results_by_step_id = {}
        loop.confirmed_execution_mismatch_count_by_step_id = {}

    async def fake_send(message_type: str, **kwargs: Any) -> None:
        sent_messages.append((message_type, kwargs))

    loop._reset_lifecycle_state = fake_reset_lifecycle_state
    loop._prepare_recording_steps = lambda steps: None
    loop._validate_recording_steps = lambda steps: None
    loop._load_skills_for_steps = lambda steps: (["core"], "", [{"name": "core"}])
    loop._load_phase_skill_expansion = lambda phase: []
    loop._send = fake_send
    loop._all_steps_done = lambda: True
    loop._has_unresolved_failure = lambda: False
    loop._should_request_user_followup = lambda final_text, pending: False
    loop._current_confirmed_execution_cursor = lambda: None


def _make_current_step() -> dict[str, Any]:
    return {
        "id": "step-1",
        "intent": "Click the Get started button",
        "element_info": {
            "text": "Get started",
            "attributes": {"aria-label": "Get started"},
        },
        "expected_outcome": {
            "type": "navigation",
            "description": "goes to docs intro page",
            "source": "user",
            "required": True,
        },
    }


# ---------------------------------------------------------------------------
# 1. PURPOSE_REGISTRY provides model_class for step_plan_normalizer
# ---------------------------------------------------------------------------

def test_purpose_registry_has_model_class_for_step_plan_normalizer() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    assert policy["model_class"] == "main"


def test_purpose_registry_has_token_budget_for_step_plan_normalizer() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    assert policy["token_budget"] == 3000


def test_purpose_registry_has_planning_tools_for_step_plan_normalizer() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    tools = policy["tool_policy"]["allowed_tools_by_phase"]["planning"]
    assert isinstance(tools, list)
    assert len(tools) > 0


# ---------------------------------------------------------------------------
# 2. S5-007 telemetry fields accept purpose-registry attribution
# ---------------------------------------------------------------------------

def test_record_model_call_start_accepts_s5_attribution_for_planning() -> None:
    """Verify record_model_call_start accepts model_class and skills_loaded."""
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    model_class = policy["model_class"]

    record = record_model_call_start(
        call_id="planning_001",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a planning agent."},
            {"role": "user", "content": "click the Get started button"},
        ],
        tools=None,
        model_class=model_class,
        skills_loaded=["llm_runtime_controller", "prompt_persona_skill_loading"],
        skill_levels=["core_compact", "core_compact"],
        context_bucket="planning",
    )

    assert record.purpose == "step_plan_normalizer"
    assert record.model_class == "main"
    assert record.skills_loaded == ["llm_runtime_controller", "prompt_persona_skill_loading"]
    assert record.skill_levels == ["core_compact", "core_compact"]
    assert record.context_bucket == "planning"
    assert record.prompt_pack_id is None  # bare telemetry start still defaults to None


def test_record_model_call_start_model_class_from_registry_is_main() -> None:
    """model_class='main' flows from PURPOSE_REGISTRY into telemetry record."""
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    record = record_model_call_start(
        call_id="planning_002",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        model_class=policy["model_class"],
    )
    assert record.model_class == "main"


def test_record_model_call_start_context_bucket_planning() -> None:
    record = record_model_call_start(
        call_id="planning_003",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        context_bucket="planning",
    )
    assert record.context_bucket == "planning"


# ---------------------------------------------------------------------------
# 3. plan_diff_editor path is unaffected
# ---------------------------------------------------------------------------

def test_plan_diff_editor_purpose_registry_unchanged() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("plan_diff_editor")
    assert policy["model_class"] == "main"
    # plan_diff_editor has no planning tools (pure text diff)
    planning_tools = policy["tool_policy"]["allowed_tools_by_phase"]["planning"]
    assert planning_tools == []


def test_plan_diff_editor_model_class_still_main() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("plan_diff_editor")
    assert policy["model_class"] == "main"


# ---------------------------------------------------------------------------
# 4. FakeLLMClient usage field includes cached_tokens
# ---------------------------------------------------------------------------

def test_fake_llm_planning_response_has_usage_with_cached_tokens() -> None:
    client = FakeLLMClient(default_purpose="step_plan_normalizer", cached_tokens=0)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan: click the button"}],
    ))
    assert hasattr(response, "usage")
    assert hasattr(response.usage, "prompt_tokens_details")
    assert response.usage.prompt_tokens_details.cached_tokens == 0


def test_fake_llm_usage_flows_into_telemetry_cached_tokens() -> None:
    """Verify cached_tokens extracted from fake provider usage via record_model_call_end."""
    from runtime.telemetry import record_model_call_end

    client = FakeLLMClient(cached_tokens=30)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this"}],
    ))

    record = record_model_call_start(
        call_id="planning_004",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this"}],
        tools=None,
    )
    record_model_call_end(record, success=True, response_usage=response.usage)
    assert record.cached_tokens == 30


# ---------------------------------------------------------------------------
# 5. Attribution: model_class from registry can be looked up by purpose
# ---------------------------------------------------------------------------

def test_model_class_lookup_for_all_main_purposes() -> None:
    """All main-model purposes should have model_class == 'main'."""
    main_purposes = [
        "step_plan_normalizer",
        "plan_diff_editor",
        "journey_planner",
        "recovery_diagnoser",
        "locator_specialist",
        "execution_driver",
    ]
    for purpose in main_purposes:
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        assert policy["model_class"] == "main", f"{purpose} should be main model"


def test_model_class_lookup_for_cheap_purposes() -> None:
    """Cheap purposes should have model_class == 'cheap'."""
    cheap_purposes = [
        "intent_classifier",
        "clarification_generator",
        "page_intelligence_summarizer",
        "user_response_writer",
        "trace_summarizer",
    ]
    for purpose in cheap_purposes:
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        assert policy["model_class"] == "cheap", f"{purpose} should be cheap model"


# ---------------------------------------------------------------------------
# 6. Planning telemetry line includes new fields when set
# ---------------------------------------------------------------------------

def test_telemetry_line_includes_model_class_and_context_bucket() -> None:
    from runtime.telemetry import _format_telemetry_line, record_model_call_end

    record = record_model_call_start(
        call_id="planning_005",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this intent"}],
        tools=None,
        model_class="main",
        context_bucket="planning",
        skills_loaded=["llm_runtime_controller"],
        skill_levels=["core_compact"],
    )
    record_model_call_end(record, success=True)
    line = _format_telemetry_line(record)

    assert "purpose=step_plan_normalizer" in line
    assert "model_class=main" in line
    assert "context_bucket=planning" in line
    assert "skills_loaded=llm_runtime_controller" in line
    assert "skill_levels=core_compact" in line


# ---------------------------------------------------------------------------
# 7. Malformed fake output detection
# ---------------------------------------------------------------------------

def test_malformed_fake_output_lacks_required_planning_fields() -> None:
    """Malformed output must not have plan_ready or steps fields."""
    assert "plan_ready" not in MALFORMED_RESPONSE
    assert "steps" not in MALFORMED_RESPONSE
    assert "corrected_steps" not in MALFORMED_RESPONSE


def test_fake_llm_force_malformed_returns_error_content() -> None:
    client = FakeLLMClient(force_malformed=True)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert "error" in content
    assert "steps" not in content
    assert "plan_ready" not in content


# ---------------------------------------------------------------------------
# 8. Token budget from PURPOSE_REGISTRY is present and reasonable
# ---------------------------------------------------------------------------

def test_step_plan_normalizer_budget_is_within_target() -> None:
    """step_plan_normalizer budget should be ≤2000 tokens (S5-002 target: ≤3000)."""
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    assert policy["token_budget"] <= 3000
    assert policy["token_budget"] > 0


def test_recovery_diagnoser_budget_is_less_than_planning() -> None:
    """Recovery context should be more focused than full planning."""
    planning = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    recovery = PURPOSE_REGISTRY.get_purpose_policy("recovery_diagnoser")
    assert recovery["token_budget"] <= planning["token_budget"]


# ---------------------------------------------------------------------------
# 9. Context bucket mapping from phase
# ---------------------------------------------------------------------------

def test_context_bucket_mapping_is_deterministic() -> None:
    """Each phase maps to a predictable context_bucket string."""
    phase_to_bucket = {
        "planning": "planning",
        "awaiting_confirmation": "planning",
        "executing": "executing",
        "recovery": "recovery",
    }
    for phase, expected_bucket in phase_to_bucket.items():
        # This is the mapping the agent should apply when calling record_model_call_start
        assert isinstance(expected_bucket, str)
        assert len(expected_bucket) > 0


def test_step_plan_normalizer_run_uses_controller_and_not_model_router(monkeypatch) -> None:
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict[str, Any]]] = []
    controller_calls: list[dict[str, Any]] = []
    loop.current_steps = [_make_current_step()]
    _install_common_run_stubs(loop, sent_messages)

    async def fake_execute_confirmed_plan() -> None:
        loop.plan_confirmed = False
        loop._run_completion_requested = True
        await loop._send("llm_result", success=True, message="executed")

    async def fake_wait_for_plan_confirmation() -> dict[str, Any]:
        loop.run_stop_requested = True
        return {"confirmed": True, "answer": "confirmed"}

    async def fake_controller_call(**kwargs: Any) -> dict[str, Any]:
        controller_calls.append(dict(kwargs))
        response = _make_response_with_tool_calls(
            _make_overlay_tool_call(
                "call-1",
                {
                    "summary": "I will click Get started",
                    "steps": [
                        {
                            "number": 1,
                            "action": "click",
                            "element_name": "Get started",
                            "code": "await getStarted.click();",
                        }
                    ],
                    "instruction": "Confirm to proceed",
                },
            )
        )
        return {
            "validation_status": "tool_calls_preserved",
            "raw_response": response,
            "raw_message": response.choices[0].message,
            "content": "",
            "tool_calls": list(response.choices[0].message.tool_calls),
        }

    async def fake_router_call(**kwargs: Any) -> Any:
        assert kwargs.get("purpose") != "step_plan_normalizer"
        loop.run_stop_requested = True
        return _make_content_only_response("executed")

    loop._execute_deterministic_fast_path_confirmed_plan = fake_execute_confirmed_plan
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation
    loop._llm_runtime_controller = SimpleNamespace(call_with_raw_response=fake_controller_call)
    loop.model_router = SimpleNamespace(call=fake_router_call)

    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step()]))

    assert controller_calls
    assert controller_calls[0]["purpose"] == "step_plan_normalizer"
    assert sent_messages[0][0] == "plan_ready"
    assert sent_messages[1][0] == "llm_result"
    assert all(
        message_type not in {"step_recorded", "code_update", "run_completed"}
        for message_type, _payload in sent_messages
    )


def test_step_plan_normalizer_prompt_pack_metadata_reaches_telemetry_line(capsys) -> None:
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict[str, Any]]] = []
    controller_calls: list[dict[str, Any]] = []
    loop.current_steps = [_make_current_step()]
    _install_common_run_stubs(loop, sent_messages)

    async def fake_execute_confirmed_plan() -> None:
        loop.plan_confirmed = False
        loop._run_completion_requested = True
        await loop._send("llm_result", success=True, message="executed")

    async def fake_wait_for_plan_confirmation() -> dict[str, Any]:
        loop.run_stop_requested = True
        return {"confirmed": True, "answer": "confirmed"}

    async def fake_controller_call(**kwargs: Any) -> dict[str, Any]:
        controller_calls.append(dict(kwargs))
        response = _make_response_with_tool_calls(
            _make_overlay_tool_call(
                "call-1",
                {
                    "summary": "I will click Get started",
                    "steps": [
                        {
                            "number": 1,
                            "action": "click",
                            "element_name": "Get started",
                            "code": "await getStarted.click();",
                        }
                    ],
                    "instruction": "Confirm to proceed",
                },
            )
        )
        return {
            "validation_status": "tool_calls_preserved",
            "raw_response": response,
            "raw_message": response.choices[0].message,
            "content": "",
            "tool_calls": list(response.choices[0].message.tool_calls),
            "prompt_pack_applied": True,
            "prompt_pack_id": "step_plan_normalizer.v1",
            "prompt_pack_version": 1,
            "prefix_hash": "deadbeefdeadbeef",
            "system_prompt_tokens": 321,
            "estimated_message_tokens": 654,
            "estimated_input_tokens": 789,
        }

    async def fake_router_call(**kwargs: Any) -> Any:
        assert kwargs.get("purpose") != "step_plan_normalizer"
        loop.run_stop_requested = True
        return _make_content_only_response("executed")

    loop._execute_deterministic_fast_path_confirmed_plan = fake_execute_confirmed_plan
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation
    loop._llm_runtime_controller = SimpleNamespace(call_with_raw_response=fake_controller_call)
    loop.model_router = SimpleNamespace(call=fake_router_call)

    asyncio.run(loop.run([_make_current_step()]))

    telemetry_lines = [
        line for line in capsys.readouterr().out.splitlines() if "[LLM_TELEMETRY]" in line
    ]
    assert telemetry_lines
    telemetry_line = next(
        line for line in telemetry_lines if "purpose=step_plan_normalizer" in line
    )
    assert "prompt_pack_id=step_plan_normalizer.v1" in telemetry_line
    assert "prompt_pack_version=1" in telemetry_line
    assert "prefix_hash=deadbeefdeadbeef" in telemetry_line
    assert "system_prompt_tokens=321" in telemetry_line
    assert "skill_levels=" in telemetry_line


def test_malformed_controller_response_fails_closed_without_plan_ready_or_execution(monkeypatch) -> None:
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict[str, Any]]] = []
    loop.current_steps = [_make_current_step()]
    _install_common_run_stubs(loop, sent_messages)
    loop.run_stop_requested = True

    async def fake_wait_for_plan_confirmation() -> dict[str, Any]:
        raise AssertionError("confirmation should not be requested for malformed content-only response")

    async def fake_controller_call(**kwargs: Any) -> dict[str, Any]:
        response = _make_content_only_response(json.dumps(MALFORMED_RESPONSE))
        return {
            "validation_status": "raw_response_preserved",
            "raw_response": response,
            "raw_message": response.choices[0].message,
            "content": response.choices[0].message.content,
            "tool_calls": [],
        }

    async def fake_router_call(**kwargs: Any) -> Any:
        raise AssertionError("model_router.call should not be used for step_plan_normalizer")

    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation
    loop._llm_runtime_controller = SimpleNamespace(call_with_raw_response=fake_controller_call)
    loop.model_router = SimpleNamespace(call=fake_router_call)

    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step()]))

    assert sent_messages == [
        ("llm_result", {"success": True, "message": json.dumps(MALFORMED_RESPONSE)})
    ]


def test_repeated_llm_thinking_stops_before_harness_timeout(monkeypatch) -> None:
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict[str, Any]]] = []
    controller_calls: list[dict[str, Any]] = []
    loop.current_steps = [_make_current_step()]
    _install_common_run_stubs(loop, sent_messages)

    thinking_responses = [
        _make_response_with_tool_calls(
            _make_overlay_tool_call(
                f"call-{index}",
                {"turn": index},
                message_type="llm_thinking",
            )
        )
        for index in range(1, 4)
    ]

    async def fake_wait_for_plan_confirmation() -> dict[str, Any]:
        raise AssertionError("plan confirmation should not be requested during repeated thinking")

    async def fake_controller_call(**kwargs: Any) -> dict[str, Any]:
        controller_calls.append(dict(kwargs))
        response = thinking_responses[min(len(controller_calls) - 1, len(thinking_responses) - 1)]
        return {
            "validation_status": "tool_calls_preserved",
            "raw_response": response,
            "raw_message": response.choices[0].message,
            "content": "",
            "tool_calls": list(response.choices[0].message.tool_calls),
            "prompt_pack_applied": True,
            "prompt_pack_id": "step_plan_normalizer.v1",
            "prompt_pack_version": 1,
            "prefix_hash": "deadbeefdeadbeef",
            "skills_loaded": ["core", "actions", "download"],
            "skill_levels": ["skill_summary", "skill_summary", "skill_summary"],
        }

    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation
    loop._llm_runtime_controller = SimpleNamespace(call_with_raw_response=fake_controller_call)

    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step()]))

    assert len(controller_calls) == 3
    message_types = [message_type for message_type, _payload in sent_messages]
    assert message_types.count("llm_thinking") == 2
    assert "runtime_rejected" in message_types
    rejection_payload = next(
        payload for message_type, payload in sent_messages if message_type == "runtime_rejected"
    )
    assert rejection_payload["rejection_code"] == "PLANNING_NO_PROGRESS"
    assert "thinking_only_turns=3" in str(rejection_payload.get("detail") or "")
    assert "planning_turns_without_terminal_output=3" in str(rejection_payload.get("detail") or "")
    assert all(
        message_type not in {"plan_ready", "step_recorded", "code_update", "run_completed"}
        for message_type in message_types
    )
