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


def _build_loop_for_completion_test(monkeypatch):
    step_context = _make_step_context()
    success_record = _make_success_record(step_context)
    sent_messages: list[tuple[str, dict[str, object]]] = []
    transition_phases: list[str] = []
    call_counter = {"count": 0}

    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = object()
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = "idle"
    original_set_phase = loop.phase_tracker.set_phase

    def recording_set_phase(new_phase, reason=None, step_id=None):
        transition_phases.append(new_phase)
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
    loop.llm_policy_gateway = SimpleNamespace(
        decide=lambda **kwargs: SimpleNamespace(
            model_needed=True,
            purpose="main_orchestrator",
            phase="planning",
            allowed_tools=[],
            context_level="normal",
            schema_id=None,
            budget="default",
            deterministic_candidate_allowed=False,
            fallback="main_orchestrator",
            requires_confirmation=True,
        )
    )

    async def fake_fast_path(steps):
        return False

    loop._try_deterministic_fast_path = fake_fast_path

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

    async def fake_action_click(args):
        locator = str(args.get("locator") or "")
        return {"success": True, "error": None, "locator": locator}

    loop._tool_action_click = fake_action_click

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
                name="action_click",
                arguments=json.dumps(
                    {
                        "step_id": "step-1",
                        "step_number": 1,
                        "locator": 'get_by_role("button", name="Submit")',
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
    return loop, sent_messages, transition_phases, call_counter


def test_all_steps_resolved_requires_awaiting_step_record_to_clear():
    loop = AgentLoop.__new__(AgentLoop)
    step_context = _make_step_context()
    step_context["status"] = "recorded"
    loop._recording_steps = [step_context]
    loop.plan_confirmed = True
    loop._awaiting_step_record = True
    loop.pending_recovery = False
    loop._pending_failure_followup = False
    loop.active_step_id = None
    loop.active_failed_step_id = None

    assert loop._all_steps_resolved() is False

    loop._awaiting_step_record = False

    assert loop._all_steps_resolved() is True


def test_pending_recovery_blocks_completion() -> None:
    loop = AgentLoop.__new__(AgentLoop)
    step_context = _make_step_context()
    step_context["status"] = "recorded"
    loop._recording_steps = [step_context]
    loop.plan_confirmed = True
    loop._awaiting_step_record = False
    loop.pending_recovery = True
    loop._pending_failure_followup = False
    loop.active_step_id = None
    loop.active_failed_step_id = None

    assert loop._all_steps_resolved() is False

    loop.pending_recovery = False

    assert loop._all_steps_resolved() is True


def test_completion_guard_stops_before_second_model_call(monkeypatch):
    loop, sent_messages, transition_phases, call_counter = _build_loop_for_completion_test(
        monkeypatch
    )

    asyncio.run(loop.run([{"id": "step-1"}]))

    assert call_counter["count"] == 1
    assert loop._run_completion_requested is True
    assert sent_messages and sent_messages[0][0] == "step_recorded"
    assert "failed" not in transition_phases
