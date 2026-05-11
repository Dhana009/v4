"""BUG-S5-013-007: Planner convergence contract tests.

Tests that verify the planning loop converges correctly on:
1. Adversarial DOM exploration sequence (llm_thinking → dom_extract → content-only)
2. Content-only responses counted as non-terminal by the guard
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

import agent as agent_module
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker
from runtime.planning_loop_guard import (
    PlanningLoopGuardState,
    advance_planning_loop_guard,
    inspect_planning_response,
)
from runtime.telemetry import record_model_call_start, record_model_call_end


# ---------------------------------------------------------------------------
# Shared helpers (mirror test_planning_through_controller_fake_model.py)
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
            arguments=json.dumps({"message_type": message_type, "payload": payload}),
        ),
    )


def _make_dom_extract_tool_call(call_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="dom_extract",
            arguments=json.dumps({"scope": "page"}),
        ),
    )


def _make_browser_get_state_tool_call(call_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="browser_get_state",
            arguments=json.dumps({}),
        ),
    )


def _make_ask_user_tool_call(call_id: str, question: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="ask_user",
            arguments=json.dumps({"question": question}),
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
    loop._pending_planning_ambiguity = None
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

    async def fake_dispatch_tool(tool_name: str, args: dict) -> dict:
        """Stub all tool dispatch to avoid browser-not-launched errors in unit tests."""
        if tool_name == "browser_get_state":
            return {"url": "http://example.test/ambiguous.html", "title": "Ambiguous Actions Fixture"}
        if tool_name == "dom_extract":
            return {
                "elements": "Profile Settings Billing Profile Shipping Profile",
                "page_intelligence": {
                    "headings": ["Profile Settings", "Billing Profile", "Shipping Profile"],
                    "sections": ["Billing Profile", "Shipping Profile"],
                    "ambiguities": ["Multiple profile sections are present"],
                },
            }
        return {"success": True, "result": f"stub:{tool_name}"}

    async def fake_tool_ask_user(args: dict[str, Any]) -> dict[str, Any]:
        sent_messages.append((
            "clarification_needed",
            {
                "question": str(args.get("question") or ""),
                "options": list(args.get("options") or []),
            },
        ))
        return {"answer": "Billing Profile", "event_type": "option_selected", "success": True}

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
    loop._dispatch_tool = fake_dispatch_tool
    loop._tool_ask_user = fake_tool_ask_user


def _make_current_step() -> dict[str, Any]:
    return {
        "id": "step-1",
        "intent": "Click Save",
        "element_info": {"text": "Save"},
        "expected_outcome": {
            "type": "state_change",
            "description": "save applied",
            "source": "user",
            "required": True,
        },
    }


# ---------------------------------------------------------------------------
# A2: Adversarial convergence test
# ---------------------------------------------------------------------------

def test_adversarial_dom_exploration_sequence_terminates_without_timeout(monkeypatch) -> None:
    """Fake LLM sequence modelling live paid failure:
      turn 1: send_to_overlay(message_type='llm_thinking')
      turn 2: browser_get_state({})
      turn 3: dom_extract({'scope': 'page'}) returning 3 Profile sections
      turn 4: plain text assistant message, no tool call

    Expected:
    - ambiguity evidence routes to clarification before any success lifecycle
    - content-only planning stays non-terminal
    - no step_recorded, no code_update, no run_completed emitted
    - no pre-confirm browser action dispatched
    """
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict[str, Any]]] = []
    controller_calls: list[dict[str, Any]] = []
    loop.current_steps = [_make_current_step()]
    _install_common_run_stubs(loop, sent_messages)

    # Four turn sequence mirroring the live paid failure
    adversarial_responses = [
        # Turn 1: llm_thinking (non-terminal, guard allows with convergence pressure)
        _make_response_with_tool_calls(
            _make_overlay_tool_call("call-1", {"text": "Inspecting page..."}, message_type="llm_thinking")
        ),
        # Turn 2: browser_get_state (non-terminal DOM exploration)
        _make_response_with_tool_calls(
            _make_browser_get_state_tool_call("call-2")
        ),
        # Turn 3: dom_extract returning 3 Profile sections (non-terminal)
        _make_response_with_tool_calls(
            _make_dom_extract_tool_call("call-3")
        ),
        # Turn 4: plain text — no tool call at all (the live failure mode)
        _make_content_only_response(
            "The page has Profile Settings, Billing Profile, and Shipping Profile sections. "
            "It is ambiguous which one the user wants to save."
        ),
    ]

    async def fake_wait_for_plan_confirmation() -> dict[str, Any]:
        raise AssertionError("plan confirmation must not be requested for adversarial sequence")

    async def fake_controller_call(**kwargs: Any) -> dict[str, Any]:
        controller_calls.append(dict(kwargs))
        idx = min(len(controller_calls) - 1, len(adversarial_responses) - 1)
        response = adversarial_responses[idx]
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
            "skills_loaded": ["core", "actions", "download"],
            "skill_levels": ["skill_summary", "skill_summary", "skill_summary"],
        }

    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation
    loop._llm_runtime_controller = SimpleNamespace(call_with_raw_response=fake_controller_call)

    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    # Must terminate without hang
    _run(loop.run([_make_current_step()]))

    message_types = [mt for mt, _ in sent_messages]

    assert "clarification_needed" in message_types, (
        f"Expected clarification_needed but got: {message_types}"
    )
    clarification_payload = next(
        payload for mt, payload in sent_messages if mt == "clarification_needed"
    )
    assert "Multiple plausible targets were found" in clarification_payload["question"]
    assert clarification_payload["options"] == [
        "Profile Settings",
        "Billing Profile",
        "Shipping Profile",
    ]

    # No execution events
    assert "step_recorded" not in message_types
    assert "code_update" not in message_types
    assert "run_completed" not in message_types
    assert "plan_ready" not in message_types


def test_ambiguous_dom_extract_builds_explicit_ask_user_instruction() -> None:
    loop = _make_agent_loop()

    loop._update_planning_ambiguity_from_tool_result(
        "dom_extract",
        {
            "page_intelligence": {
                "headings": ["Profile Settings", "Billing Profile", "Shipping Profile"],
                "sections": ["Billing Profile", "Shipping Profile"],
            }
        },
    )

    instruction = loop._build_pending_ambiguity_instruction()

    assert instruction is not None
    assert "Multiple plausible targets were found" in instruction
    assert "Call ask_user with options" in instruction
    assert "Do not continue DOM exploration" in instruction
    assert "Do not answer in plain text" in instruction


# ---------------------------------------------------------------------------
# A3: Content-only response must be non-terminal in the guard
# ---------------------------------------------------------------------------

def test_content_only_planning_response_is_non_terminal() -> None:
    """A plain-text assistant message with no tool calls must be treated as
    non-terminal by the planning loop guard — it should NOT set terminal_reason,
    and must increment planning_turns_without_terminal_output.
    """
    content_only_message = SimpleNamespace(
        content="The page has three Profile sections and it is unclear which one to save.",
        tool_calls=[],
        role="assistant",
    )

    inspection = inspect_planning_response(content_only_message)

    # Content-only must NOT be treated as terminal
    assert inspection.terminal_reason is None, (
        f"Content-only response must not be terminal; got terminal_reason={inspection.terminal_reason!r}"
    )
    assert inspection.has_tool_calls is False
    assert inspection.thinking_only is False


def test_content_only_response_increments_no_progress_counter() -> None:
    """The guard must increment planning_turns_without_terminal_output for content-only turns."""
    state = PlanningLoopGuardState()
    content_only_message = SimpleNamespace(
        content="I need more information about the page layout to proceed.",
        tool_calls=[],
        role="assistant",
    )

    result = advance_planning_loop_guard(
        state,
        content_only_message,
        purpose="step_plan_normalizer",
    )

    assert result.should_stop is False
    assert result.state.planning_turns_without_terminal_output == 1, (
        "Content-only turn must increment planning_turns_without_terminal_output"
    )
    assert result.inspection.terminal_reason is None


def test_repeated_content_only_responses_eventually_trigger_no_progress() -> None:
    """Three consecutive content-only responses must trigger PLANNING_NO_PROGRESS."""
    state = PlanningLoopGuardState()
    content_only_message = SimpleNamespace(
        content="Still thinking about the page...",
        tool_calls=[],
        role="assistant",
    )

    for _ in range(3):
        result = advance_planning_loop_guard(state, content_only_message)
        state = result.state

    # 4th content-only turn should exceed the max
    final = advance_planning_loop_guard(state, content_only_message)
    assert final.should_stop is True
    assert final.reason_code == "PLANNING_NO_PROGRESS"
