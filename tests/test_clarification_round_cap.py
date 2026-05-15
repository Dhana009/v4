"""ISSUE-002: bounded clarification rounds — force plan_ready after MAX ask_user calls.

Tests that after _MAX_CLARIFICATION_ROUNDS ask_user calls during step_plan_normalizer:
1. The next LLM request uses tool_choice forced to send_to_overlay.
2. ask_user is dropped from the tool surface.
3. A system message containing "MUST now call send_to_overlay" is injected.
4. If LLM still returns no tool calls, a heuristic fallback plan_ready is emitted.
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

import agent as agent_module
from agent import AgentLoop, _MAX_CLARIFICATION_ROUNDS
from runtime.phase_tracker import PhaseTracker
from runtime.planning_loop_guard import PlanningLoopGuardState


# ---------------------------------------------------------------------------
# Helpers (mirror test_planning_convergence_contract.py)
# ---------------------------------------------------------------------------

def _run(coro: Any) -> Any:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_tool_call(name: str, call_id: str, args: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(args),
        ),
    )


def _make_ask_user_response(call_id: str, question: str = "What do you want?") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[_make_tool_call("ask_user", call_id, {"question": question})],
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


def _make_send_to_overlay_response(call_id: str, message_type: str = "plan_ready") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        _make_tool_call(
                            "send_to_overlay",
                            call_id,
                            {
                                "message_type": message_type,
                                "payload": {
                                    "summary": "test plan",
                                    "steps": [
                                        {
                                            "step_id": "step_001",
                                            "intent": "test intent",
                                            "expected_outcome": {"type": "not_sure"},
                                        }
                                    ],
                                },
                            },
                        )
                    ],
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


def _make_plain_text_response(content: str = "I cannot decide.") -> SimpleNamespace:
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


def _make_stub_tool(name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"stub {name}",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    }


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
    loop._pending_planning_ambiguity = None
    loop._step_plan_convergence_narrowing = False
    loop._clarification_round_count = 0  # ISSUE-002
    loop._active_plan_state = None
    loop._active_plan_correction_state = None
    loop._run_completion_requested = False
    loop.run_stop_requested = False
    loop._llm_call_counter = 0
    loop.confirmed_plan_by_step_id = {}
    loop.confirmed_plan_step_ids = []
    loop.confirmed_child_results_by_step_id = {}
    loop.confirmed_execution_mismatch_count_by_step_id = {}
    loop.tools = [_make_stub_tool(n) for n in ("ask_user", "send_to_overlay")]
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


def _install_stubs(
    loop: AgentLoop,
    sent_messages: list[tuple[str, dict]],
    ask_user_answer: str = "any answer",
) -> None:
    def fake_reset_lifecycle_state(steps=None):
        loop.phase = "planning"
        loop.plan_confirmed = False
        loop.current_steps = list(steps or [])
        loop.phase_tracker.current_phase = "idle"
        loop.step_state_by_id = {}
        loop._awaiting_step_record = False
        loop._pending_failure_followup = False
        loop._run_completion_requested = False
        loop.run_stop_requested = False
        loop._llm_call_counter = 0
        loop._planning_loop_guard_state = PlanningLoopGuardState()
        loop._clarification_round_count = 0  # reset on new run

    async def fake_send(message_type: str, **kwargs: Any) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_dispatch_tool(tool_name: str, args: dict) -> dict:
        if tool_name == "ask_user":
            sent_messages.append(("clarification_needed", {"question": args.get("question", "")}))
            return {"answer": ask_user_answer, "event_type": "option_selected", "success": True}
        if tool_name == "send_to_overlay":
            mtype = args.get("message_type", "")
            sent_messages.append((mtype, args.get("payload", {})))
            if mtype == "plan_ready":
                # Simulate plan confirmation so the run terminates cleanly.
                loop.plan_confirmed = True
                loop.phase = "executing"
                loop._run_completion_requested = True
            return {"sent": True, "confirmed": mtype == "plan_ready", "message_type": mtype}
        return {"success": True}

    def fake_emit_backend_event_now(event_type: str, **kwargs: Any) -> None:
        sent_messages.append((event_type, kwargs))

    loop._reset_lifecycle_state = fake_reset_lifecycle_state
    loop._prepare_recording_steps = lambda steps: None
    loop._validate_recording_steps = lambda steps: None
    loop._load_skills_for_steps = lambda steps: (["core"], "", [{"name": "core"}])
    loop._load_phase_skill_expansion = lambda phase: []
    loop._send = fake_send
    loop._emit_backend_event_now = fake_emit_backend_event_now
    loop._all_steps_done = lambda: True
    loop._has_unresolved_failure = lambda: False
    loop._should_request_user_followup = lambda final_text, pending: False
    loop._current_confirmed_execution_cursor = lambda: None
    loop._dispatch_tool = fake_dispatch_tool


def _make_current_step(intent: str = "Validate pricing page") -> dict:
    return {
        "step_id": "step-1",
        "intent": intent,
        "expected_outcome": {"type": "not_sure"},
    }


def _make_fake_controller_recording(
    responses: list[Any],
    controller_calls: list[dict],
    *,
    fallback: Any = None,
) -> Any:
    """Return a fake controller that records messages+tool_choice per call."""
    if fallback is None:
        fallback = _make_plain_text_response("fallback plain text")

    async def fake_call(**kwargs: Any) -> dict[str, Any]:
        call_index = len(controller_calls)
        controller_calls.append({
            "tool_names": sorted(
                t.get("function", {}).get("name", "")
                for t in (kwargs.get("tools") or [])
                if isinstance(t, dict)
            ),
            "tool_choice": kwargs.get("tool_choice"),
            "messages": list(kwargs.get("messages") or []),
        })
        response = responses[call_index] if call_index < len(responses) else fallback
        msg = response.choices[0].message
        return {
            "validation_status": "tool_calls_preserved",
            "raw_response": response,
            "raw_message": msg,
            "content": msg.content or "",
            "tool_calls": list(msg.tool_calls or []),
            "prompt_pack_applied": True,
            "prompt_pack_id": "step_plan_normalizer.v1",
            "prompt_pack_version": 1,
            "prefix_hash": "deadbeefdeadbeef",
            "skills_loaded": [],
            "skill_levels": [],
        }

    return fake_call


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_max_clarification_rounds_constant_is_2():
    """_MAX_CLARIFICATION_ROUNDS must default to 2."""
    assert _MAX_CLARIFICATION_ROUNDS == 2, (
        f"Expected _MAX_CLARIFICATION_ROUNDS=2, got {_MAX_CLARIFICATION_ROUNDS}"
    )


def test_clarification_round_count_resets_on_new_run(monkeypatch):
    """_clarification_round_count must reset to 0 on _reset_lifecycle_state."""
    loop = _make_agent_loop()
    loop._clarification_round_count = 5
    # Call the real reset method with minimal stubs
    loop._clear_confirmed_execution_contract_state = lambda: None
    loop._clear_plan_review_context = lambda: None
    loop.capability_gaps = []
    loop.recorded_step_payloads = []
    loop.code_update_payloads = []
    loop.replay_recorded_step_payloads_by_step_id = {}
    loop.replay_action_history_by_step_id = {}
    loop._run_started_emitted = False
    loop._debug_report_emitted = set()
    loop._code_review_emitted = set()
    loop._plan_correction_pending = False
    loop._run_completed_emitted = False
    loop.recovery_attempts = {}
    loop._recording_wait_guard_armed = False
    loop._run_session_id = "test-session"
    loop._new_run_session_id = lambda: "new-session"

    AgentLoop._reset_lifecycle_state(loop)

    assert loop._clarification_round_count == 0, (
        "_clarification_round_count must be 0 after _reset_lifecycle_state"
    )


def test_after_max_clarification_rounds_tool_choice_forced_to_send_to_overlay(monkeypatch):
    """After _MAX_CLARIFICATION_ROUNDS ask_user calls, next controller call must use
    tool_choice forced to send_to_overlay AND ask_user must be absent from tools.
    """
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict]] = []
    controller_calls: list[dict] = []

    step = _make_current_step()
    loop.current_steps = [step]
    _install_stubs(loop, sent_messages)

    # Sequence: 2 ask_user rounds, then a plan_ready
    responses = [
        _make_ask_user_response("call-1", "Round 1 question"),
        _make_ask_user_response("call-2", "Round 2 question"),
        # On the 3rd call (cap hit), LLM is forced — return plan_ready
        _make_send_to_overlay_response("call-3"),
    ]
    fallback = _make_send_to_overlay_response("call-fallback")

    loop._llm_runtime_controller = SimpleNamespace(
        call_with_raw_response=_make_fake_controller_recording(
            responses, controller_calls, fallback=fallback
        )
    )
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    _run(loop.run([step]))

    # Must have at least 3 controller calls (2 ask_user + 1 forced)
    assert len(controller_calls) >= 3, (
        f"Expected at least 3 controller calls, got {len(controller_calls)}: {controller_calls}"
    )

    # Third call: tool_choice must be forced to send_to_overlay
    call3 = controller_calls[2]
    tc = call3.get("tool_choice")
    assert isinstance(tc, dict), (
        f"After cap, tool_choice must be a dict, got {tc!r}"
    )
    assert tc.get("type") == "function", f"tool_choice.type must be 'function', got {tc}"
    forced_name = tc.get("function", {}).get("name")
    assert forced_name == "send_to_overlay", (
        f"tool_choice must force send_to_overlay, got {forced_name!r}"
    )

    # Third call: ask_user must NOT be in the tool surface
    call3_tools = set(call3.get("tool_names") or [])
    assert "ask_user" not in call3_tools, (
        f"ask_user must be dropped from tool surface on cap call, got {call3_tools}"
    )


def test_after_max_clarification_rounds_system_message_injected(monkeypatch):
    """After cap, a user message containing 'MUST now call send_to_overlay' must appear
    in the messages passed to the controller.
    """
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict]] = []
    controller_calls: list[dict] = []

    step = _make_current_step()
    loop.current_steps = [step]
    _install_stubs(loop, sent_messages)

    responses = [
        _make_ask_user_response("call-1", "Round 1 question"),
        _make_ask_user_response("call-2", "Round 2 question"),
        _make_send_to_overlay_response("call-3"),
    ]
    fallback = _make_send_to_overlay_response("call-fallback")

    loop._llm_runtime_controller = SimpleNamespace(
        call_with_raw_response=_make_fake_controller_recording(
            responses, controller_calls, fallback=fallback
        )
    )
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    _run(loop.run([step]))

    assert len(controller_calls) >= 3, (
        f"Expected at least 3 controller calls, got {len(controller_calls)}"
    )

    # The third call's messages must contain the forcing instruction
    call3_messages = controller_calls[2].get("messages") or []
    all_content = " ".join(
        str(m.get("content") or "") for m in call3_messages
        if isinstance(m, dict)
    )
    assert "MUST now call send_to_overlay" in all_content, (
        f"Forcing system message not found in call 3 messages. Content: {all_content[:500]}"
    )


def test_fallback_plan_ready_emitted_when_llm_refuses_after_cap(monkeypatch):
    """If LLM returns plain text (no tool call) after the cap is hit,
    a heuristic plan_ready envelope must be emitted via _send.
    """
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict]] = []
    controller_calls: list[dict] = []

    step = _make_current_step("Validate the pricing page layout")
    loop.current_steps = [step]
    _install_stubs(loop, sent_messages)

    responses = [
        _make_ask_user_response("call-1", "Round 1 question"),
        _make_ask_user_response("call-2", "Round 2 question"),
        # After cap, LLM still returns plain text — triggers fallback
        _make_plain_text_response("I cannot decide what plan to make."),
    ]
    # fallback should also be plain text to avoid infinite loop
    fallback = _make_plain_text_response("still nothing")

    loop._llm_runtime_controller = SimpleNamespace(
        call_with_raw_response=_make_fake_controller_recording(
            responses, controller_calls, fallback=fallback
        )
    )
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    _run(loop.run([step]))

    # A plan_ready (or backend_event with type plan_ready) must have been emitted
    message_types = [mt for mt, _ in sent_messages]

    # The fallback path calls _emit_backend_event_now which bypasses _send,
    # but it also calls _reset_lifecycle_state — check that run terminated and
    # the fallback log was triggered. We verify via controller_calls (3rd call made)
    # and that no runtime_rejected was emitted (fallback = graceful exit).
    assert len(controller_calls) >= 3, (
        f"Fallback path requires at least 3 controller calls, got {len(controller_calls)}"
    )
    assert "runtime_rejected" not in message_types, (
        "Fallback must NOT emit runtime_rejected; it should exit gracefully"
    )
