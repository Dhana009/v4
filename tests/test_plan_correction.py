from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import agent as agent_module
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


def _make_current_step() -> dict[str, object]:
    return {
        "id": "step-1",
        "intent": "Check that Get started is visible and click it",
        "element_info": {
            "text": "Get started",
            "attributes": {"aria-label": "Get started"},
        },
    }


def _make_plan_payload(step_specs: list[dict[str, object]], summary: str) -> dict[str, object]:
    return {
        "summary": summary,
        "steps": step_specs,
        "instruction": "Confirm to proceed",
    }


def _make_tool_call(call_id: str, payload: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="send_to_overlay",
            arguments=json.dumps(
                {
                    "message_type": "plan_ready",
                    "payload": payload,
                }
            ),
        ),
    )


def _make_loop() -> AgentLoop:
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
    return loop


def _install_common_run_stubs(loop: AgentLoop, sent_messages: list[tuple[str, dict[str, object]]]) -> None:
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
        loop._clear_plan_review_context()
        loop._run_completion_requested = False
        loop.run_stop_requested = False
        loop._llm_call_counter = 0

    async def fake_send(msg_type, **kwargs):
        sent_messages.append((msg_type, kwargs))

    loop._reset_lifecycle_state = fake_reset_lifecycle_state
    loop._prepare_recording_steps = lambda steps: None
    loop._load_skills_for_steps = lambda steps: (["core"], "", [{"name": "core"}])
    loop._load_phase_skill_expansion = lambda phase: []
    loop._send = fake_send


def _plan_ready_response(call_id: str, step_specs: list[dict[str, object]], summary: str) -> SimpleNamespace:
    tool_call = _make_tool_call(call_id, _make_plan_payload(step_specs, summary))
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="", tool_calls=[tool_call])
            )
        ]
    )


def _final_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text, tool_calls=[])
            )
        ]
    )


def test_plan_correction_message_uses_active_plan_context() -> None:
    loop = _make_loop()
    loop.current_steps = [_make_current_step()]
    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {
            "confirmed": False,
            "correction": "Only verify it is visible, do not click",
        }

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _make_plan_payload(
                    [
                        {
                            "number": 1,
                            "action": "assert",
                            "element_name": "Get started",
                            "code": "await expect(getStarted).toBeVisible();",
                        },
                        {
                            "number": 2,
                            "action": "click",
                            "element_name": "Get started",
                            "code": "await getStarted.click();",
                        },
                    ],
                    "I will check that Get started is visible and click it",
                ),
            }
        )
    )

    note = loop._append_plan_correction_message(result["correction"])

    assert result == {
        "confirmed": False,
        "correction": "Only verify it is visible, do not click",
        "phase": "planning",
    }
    assert loop.phase == "planning"
    assert loop.plan_confirmed is False
    assert loop.last_plan_ready_payload is None
    assert loop.last_plan_step_ids == []
    assert loop.last_plan_summary is None
    assert loop.last_plan_original_user_intent is None
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert len(sent_messages[0][1]["steps"][0]["children"]) == 2
    assert "User corrected the current plan." in note
    assert 'Correction: "Only verify it is visible, do not click"' in note
    assert 'Previous plan summary: "I will check that Get started is visible and click it"' in note
    assert "1. Check that Get started is visible and click it" in note
    assert "   - op_1 assert Get started is visible" in note
    assert "   - op_2 click Get started" in note
    assert note == loop.llm.messages[-1]["content"]


def test_plan_confirmation_still_enters_execution_and_clears_context() -> None:
    loop = _make_loop()
    loop.current_steps = [_make_current_step()]
    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _make_plan_payload(
                    [
                        {
                            "number": 1,
                            "action": "assert",
                            "element_name": "Get started",
                            "code": "await expect(getStarted).toBeVisible();",
                        }
                    ],
                    "I will check that Get started is visible",
                ),
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert loop.plan_confirmed is True
    assert loop.phase == "executing"
    assert loop.last_plan_ready_payload is None
    assert loop.last_plan_step_ids == []
    assert loop.last_plan_summary is None
    assert loop.last_plan_original_user_intent is None
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert len(sent_messages[0][1]["steps"][0]["children"]) >= 1
    assert sent_messages[0][1]["steps"][0]["children"][0]["type"] == "assert"


def test_plan_correction_triggers_replanned_plan_ready_before_execution(monkeypatch) -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    call_counter = {"count": 0}
    model_messages: list[list[dict[str, object]]] = []
    confirmation_calls = {"count": 0}

    loop.current_steps = [_make_current_step()]
    _install_common_run_stubs(loop, sent_messages)

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        confirmation_calls["count"] += 1
        if confirmation_calls["count"] == 1:
            return {
                "confirmed": False,
                "correction": "Only verify it is visible, do not click",
            }
        loop.run_stop_requested = True
        return {"confirmed": True, "answer": "confirmed"}

    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    async def fake_model_call(*args, **kwargs):
        call_counter["count"] += 1
        messages = list(kwargs.get("messages") or [])
        model_messages.append(messages)
        if call_counter["count"] == 1:
            return _plan_ready_response(
                "call-1",
                [
                    {
                        "number": 1,
                        "action": "assert",
                        "element_name": "Get started",
                        "code": "await expect(getStarted).toBeVisible();",
                    },
                    {
                        "number": 2,
                        "action": "click",
                        "element_name": "Get started",
                        "code": "await getStarted.click();",
                    },
                ],
                "I will check that Get started is visible and click it",
            )
        if call_counter["count"] == 2:
            user_messages = [message for message in messages if message.get("role") == "user"]
            assert user_messages
            correction_message = str(user_messages[-1].get("content") or "")
            assert "User corrected the current plan." in correction_message
            assert 'Correction: "Only verify it is visible, do not click"' in correction_message
            assert 'Previous plan summary: "I will check that Get started is visible and click it"' in correction_message
            assert "   - op_1 assert Get started is visible" in correction_message
            assert "   - op_2 click Get started" in correction_message
            return _plan_ready_response(
                "call-2",
                [
                    {
                        "number": 1,
                        "intent": "Check that Get started is visible",
                        "action": "assert",
                        "element_name": "Get started",
                        "code": "await expect(getStarted).toBeVisible();",
                    }
                ],
                "I will only verify that Get started is visible",
            )
        return _final_response("Done")

    loop.model_router = SimpleNamespace(call=fake_model_call)
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step()]))

    assert call_counter["count"] == 3
    assert confirmation_calls["count"] == 2
    assert len(sent_messages) == 3
    assert sent_messages[0][0] == "plan_ready"
    assert len(sent_messages[0][1]["steps"][0]["children"]) == 2
    assert sent_messages[1][0] == "plan_ready"
    assert len(sent_messages[1][1]["steps"][0]["children"]) == 1
    assert sent_messages[1][1]["steps"][0]["children"][0]["type"] == "assert"
    assert sent_messages[1][1]["steps"][0]["intent"] == "Check that Get started is visible"
    assert sent_messages[2][0] == "llm_result"
    assert loop.run_stop_requested is False
    assert loop.plan_confirmed is False
    assert any("User corrected the current plan." in str(message.get("content") or "") for message in model_messages[1])
    assert all(message_type not in {"step_recorded", "code_update"} for message_type, _ in sent_messages)
