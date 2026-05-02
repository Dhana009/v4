from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import agent as agent_module
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


def _make_step_context() -> dict[str, object]:
    return {
        "step_id": "step-1",
        "step_number": 1,
        "intent": "Click the submit button",
        "element_info": {
            "text": "Submit",
            "attributes": {"aria-label": "Submit"},
        },
        "element_name": "Submit",
        "locator": None,
        "status": "executing",
        "recorded": False,
        "last_error": None,
    }


def _make_success_record(step_context: dict[str, object]) -> dict[str, object]:
    locator = 'get_by_role("button", name="Submit")'
    return {
        "tool": "action_click",
        "action": "click",
        "locator": locator,
        "result": {"success": True, "skipped": False},
        "step_context": step_context,
        "action_context": {"locator": locator},
        "tool_args": {"locator": locator},
        "step_id": step_context["step_id"],
        "step_number": step_context["step_number"],
    }


def _build_loop_for_code_update_test(monkeypatch):
    step_context = _make_step_context()
    success_record = _make_success_record(step_context)
    sent_messages: list[tuple[str, dict[str, object]]] = []
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
        loop.last_successful_action = success_record
        loop.successful_action_by_step_id = {"step-1": success_record}
        loop._recording_steps = [step_context]
        loop._recording_step_index = 0
        loop._recorded_step_ids = set()
        loop._last_action_context = None
        loop._awaiting_step_record = True
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

    async def fake_model_call(*args, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] > 1:
            raise AssertionError("Unexpected second model call")
        tool_call = SimpleNamespace(
            id="call-1",
            type="function",
            function=SimpleNamespace(
                name="send_to_overlay",
                arguments=json.dumps(
                    {
                        "message_type": "step_recorded",
                        "payload": {
                            "step_id": "step-1",
                            "step_number": 1,
                        },
                    }
                ),
            ),
        )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="", tool_calls=[tool_call])
                )
            ]
        )

    loop.model_router = SimpleNamespace(call=fake_model_call)
    monkeypatch.setattr(
        agent_module,
        "record_model_call_start",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        agent_module,
        "record_model_call_end",
        lambda *args, **kwargs: None,
    )
    return loop, sent_messages, call_counter


def test_simple_click_recording_emits_code_update_and_stops_cleanly(monkeypatch, capsys) -> None:
    loop, sent_messages, call_counter = _build_loop_for_code_update_test(monkeypatch)

    asyncio.run(loop.run([{"id": "step-1"}]))
    captured = capsys.readouterr().out

    assert call_counter["count"] == 1
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[1][0] == "code_update"

    recorded_payload = sent_messages[0][1]
    code_update_payload = sent_messages[1][1]

    assert code_update_payload["step_id"] == recorded_payload["step_id"]
    assert code_update_payload["operation_id"] == "op_1"
    assert code_update_payload["lines"] == [recorded_payload["generated_line"]]
    assert code_update_payload["full_spec_preview"] == recorded_payload["generated_line"]
    assert isinstance(code_update_payload["diagnostics"], list)
    assert code_update_payload["diagnostics"] == []
    assert loop._run_completion_requested is True
    assert "[CODE_UPDATE] step_id=step-1 operation_id=op_1 lines=1" in captured
    assert captured.index("[CODE_UPDATE] step_id=step-1 operation_id=op_1 lines=1") < captured.index(
        "[AGENT] all steps resolved; ending run without extra LLM call"
    )
