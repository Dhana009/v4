from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import agent as agent_module
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


def _make_step_context(
    step_id: str,
    intent: str,
    element_text: str,
    aria_label: str,
) -> dict[str, object]:
    return {
        "step_id": step_id,
        "step_number": 1,
        "intent": intent,
        "element_info": {
            "text": element_text,
            "attributes": {"aria-label": aria_label},
        },
        "element_name": element_text,
        "locator": None,
        "status": "executing",
        "recorded": False,
        "last_error": None,
    }


def _make_tool_call(call_id: str, name: str, arguments: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


def _build_loop_for_multi_action_safety_test(
    monkeypatch,
    step_context: dict[str, object],
    tool_calls: list[SimpleNamespace],
):
    sent_messages: list[tuple[str, dict[str, object]]] = []
    blocked_results: list[tuple[str, dict[str, object]]] = []
    executed_actions: list[str] = []
    call_counter = {"count": 0}

    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = object()
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = "idle"
    original_set_phase = loop.phase_tracker.set_phase

    def recording_set_phase(new_phase, reason=None, step_id=None):
        return original_set_phase(new_phase, reason=reason, step_id=step_id)

    loop.phase_tracker.set_phase = recording_set_phase
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
    loop._recording_steps = []
    loop._recording_step_index = 0
    loop._recorded_step_ids = set()
    loop._last_action_context = None
    loop._awaiting_step_record = False
    loop._pending_failure_followup = False
    loop._run_completion_requested = False
    loop.run_stop_requested = False
    loop._llm_call_counter = 0
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

    def fake_reset_lifecycle_state(steps=None):
        if steps is None:
            return
        loop.phase = "planning"
        loop.plan_confirmed = True
        loop.current_steps = list(steps)
        loop.phase_tracker.current_phase = "idle"
        loop.step_state_by_id = {"step-1": step_context}
        loop.step_context_by_id = {"step-1": step_context}
        loop.active_step_id = "step-1"
        loop.active_failed_step_id = None
        loop.pending_recovery = False
        loop.completed_step_ids = set()
        loop.skipped_step_ids = set()
        loop.current_step_index = 0
        loop.last_successful_action = None
        loop.successful_action_by_step_id = {}
        loop.successful_actions_by_step_id = {}
        loop._recording_steps = [step_context]
        loop._recording_step_index = 0
        loop._recorded_step_ids = set()
        loop._last_action_context = None
        loop._awaiting_step_record = False
        loop._pending_failure_followup = False
        loop._run_completion_requested = False
        loop.run_stop_requested = False
        loop._llm_call_counter = 0

    loop._reset_lifecycle_state = fake_reset_lifecycle_state
    loop._prepare_recording_steps = lambda steps: None
    loop._load_skills_for_steps = lambda steps: (["core"], "", [{"name": "core"}])
    loop._load_phase_skill_expansion = lambda phase: []

    async def fake_send(msg_type, **kwargs):
        sent_messages.append((msg_type, kwargs))

    loop._send = fake_send

    original_append_tool_response = loop._append_tool_response

    def recording_append_tool_response(tool_call_id, result):
        blocked_results.append((tool_call_id, result))
        return original_append_tool_response(tool_call_id, result)

    loop._append_tool_response = recording_append_tool_response

    async def fake_action_click(args):
        executed_actions.append("action_click")
        locator = str(args.get("locator") or "")
        return {"success": True, "error": None, "locator": locator}

    async def fake_action_assert(args):
        executed_actions.append("action_assert")
        locator = str(args.get("locator") or "")
        assertion = str(args.get("assertion") or "visible")
        return {
            "success": True,
            "error": None,
            "locator": locator,
            "assertion": assertion,
        }

    loop._tool_action_click = fake_action_click
    loop._tool_action_assert = fake_action_assert

    async def fake_model_call(*args, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] > 1:
            raise AssertionError("Unexpected second model call")
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="", tool_calls=list(tool_calls))
                )
            ]
        )

    loop.model_router = SimpleNamespace(call=fake_model_call)
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)
    return loop, sent_messages, blocked_results, executed_actions, call_counter


def test_single_click_action_can_still_be_recorded(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Click the submit button",
        "Submit",
        "Submit",
    )
    tool_calls = [
        _make_tool_call(
            "call-1",
            "action_click",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Submit")',
            },
        ),
        _make_tool_call(
            "call-2",
            "send_to_overlay",
            {
                "message_type": "step_recorded",
                "payload": {
                    "step_id": "step-1",
                    "step_number": 1,
                },
            },
        ),
    ]

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        tool_calls,
    )

    asyncio.run(loop.run([{"id": "step-1"}]))

    assert call_counter["count"] == 1
    assert executed_actions == ["action_click"]
    assert blocked_results == []
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[0][1]["action"] == "click"
    assert sent_messages[0][1]["status"] == "success"
    assert sent_messages[0][1]["children"][0]["type"] == "click"
    assert sent_messages[1][0] == "code_update"
    assert sent_messages[1][1]["lines"] == [sent_messages[0][1]["generated_line"]]


def test_assert_and_click_both_execute_and_record_in_order(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Check that Get started is visible and click it",
        "Get started",
        "Get started",
    )
    tool_calls = [
        _make_tool_call(
            "call-1",
            "action_assert",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Get started")',
                "assertion": "visible",
            },
        ),
        _make_tool_call(
            "call-2",
            "action_click",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Get started")',
            },
        ),
        _make_tool_call(
            "call-3",
            "send_to_overlay",
            {
                "message_type": "step_recorded",
                "payload": {
                    "step_id": "step-1",
                    "step_number": 1,
                },
            },
        ),
    ]

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        tool_calls,
    )

    asyncio.run(loop.run([{"id": "step-1"}]))

    assert call_counter["count"] == 1
    assert executed_actions == ["action_assert", "action_click"]
    assert blocked_results == []
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert len(sent_messages[0][1]["children"]) == 2
    assert sent_messages[0][1]["action"] == "click"
    assert sent_messages[0][1]["status"] == "success"
    assert sent_messages[0][1]["children"][0]["type"] == "assert"
    assert sent_messages[0][1]["children"][1]["type"] == "click"
    assert sent_messages[1][0] == "code_update"
    assert len(sent_messages[1][1]["lines"]) == 2
