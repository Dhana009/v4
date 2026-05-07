from __future__ import annotations

import asyncio
from types import SimpleNamespace

from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


class SequenceQueue:
    def __init__(self, messages: list[dict[str, object]] | None = None) -> None:
        self.messages = list(messages or [])
        self.get_count = 0

    async def get(self) -> dict[str, object]:
        self.get_count += 1
        if not self.messages:
            raise AssertionError("expected another confirmation event")
        return self.messages.pop(0)

    async def put(self, item: dict[str, object]) -> None:  # noqa: ARG002
        return None


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = SequenceQueue()
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
    loop._recording_wait_guard_armed = False
    loop._pending_failure_followup = False
    loop.last_plan_ready_payload = None
    loop.last_plan_step_ids = []
    loop.last_plan_summary = None
    loop.last_plan_original_user_intent = None
    loop._active_plan_state = None
    loop._active_plan_correction_state = None
    loop._plan_correction_pending = False
    loop._run_completion_requested = False
    loop._run_completed_emitted = False
    loop.run_stop_requested = False
    loop._llm_call_counter = 0
    loop.confirmed_plan_by_step_id = {}
    loop.confirmed_plan_step_ids = []
    loop.confirmed_child_results_by_step_id = {}
    loop.confirmed_execution_mismatch_count_by_step_id = {}
    loop.capability_gaps = []
    loop.recorded_step_payloads = []
    loop.code_update_payloads = []
    loop.replay_recorded_step_payloads_by_step_id = {}
    loop.replay_action_history_by_step_id = {}
    loop.llm = SimpleNamespace(messages=[], system_prompt="", client=object(), reset=lambda: None)
    return loop


def _make_step(step_id: str) -> dict[str, object]:
    return {
        "step_id": step_id,
        "step_number": 1,
        "intent": "Check that Get started is visible and click it",
        "element_info": {
            "text": "Get started",
            "attributes": {"aria-label": "Get started"},
        },
    }


def test_reset_lifecycle_state_discards_previous_run_state_and_allocates_fresh_session() -> None:
    loop = _make_loop()
    loop._run_session_id = "run-old"
    loop._new_run_session_id = lambda: "run-new"
    loop.phase = "executing"
    loop.phase_tracker.current_phase = "executing"
    loop.plan_confirmed = True
    loop.current_steps = [_make_step("step-old")]
    loop.step_state_by_id = {"step-old": _make_step("step-old")}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "step-old"
    loop.active_failed_step_id = "step-old"
    loop.pending_recovery = True
    loop.completed_step_ids = {"step-old"}
    loop.skipped_step_ids = {"step-skip"}
    loop.current_step_index = 7
    loop.last_successful_action = {"step_context": {"step_id": "step-old", "step_number": 1}}
    loop.successful_action_by_step_id = {"step-old": {"step_id": "step-old"}}
    loop.successful_actions_by_step_id = {"step-old": [{"step_id": "step-old"}]}
    loop.last_plan_ready_payload = {"summary": "old plan", "steps": [{"step_id": "step-old"}]}
    loop.last_plan_step_ids = ["step-old"]
    loop.last_plan_summary = "old plan"
    loop.last_plan_original_user_intent = "old intent"
    loop._active_plan_state = {"plan_id": "plan-old", "run_id": "run-old", "steps": [{"step_id": "step-old"}]}
    loop._active_plan_correction_state = {"clarification_question": "old"}
    loop._plan_correction_pending = True
    loop._run_completion_requested = True
    loop._run_completed_emitted = True
    loop.recorded_step_payloads = [{"step_id": "step-old"}]
    loop.code_update_payloads = [{"step_id": "step-old"}]
    loop.replay_recorded_step_payloads_by_step_id = {"step-old": {"step_id": "step-old"}}
    loop.replay_action_history_by_step_id = {"step-old": [{"status": "recorded"}]}

    new_steps = [_make_step("step-new")]
    loop._reset_lifecycle_state(new_steps)

    assert loop.phase == "planning"
    assert loop.phase_tracker.get_phase() == "idle"
    assert loop.plan_confirmed is False
    assert loop.current_steps == new_steps
    assert loop.step_state_by_id == {}
    assert loop.step_context_by_id == {}
    assert loop.active_step_id is None
    assert loop.active_failed_step_id is None
    assert loop.pending_recovery is False
    assert loop.completed_step_ids == set()
    assert loop.skipped_step_ids == set()
    assert loop.last_successful_action is None
    assert loop.successful_action_by_step_id == {}
    assert loop.successful_actions_by_step_id == {}
    assert loop.last_plan_ready_payload is None
    assert loop.last_plan_step_ids == []
    assert loop.last_plan_summary is None
    assert loop.last_plan_original_user_intent is None
    assert loop._active_plan_state is None
    assert loop._active_plan_correction_state is None
    assert loop._plan_correction_pending is False
    assert loop._run_completion_requested is False
    assert loop._run_completed_emitted is False
    assert loop.recorded_step_payloads == []
    assert loop.code_update_payloads == []
    assert loop.replay_recorded_step_payloads_by_step_id == {}
    assert loop.replay_action_history_by_step_id == {}
    assert loop._run_session_id == "run-new"


def test_previous_run_confirmation_is_rejected_against_current_run_context() -> None:
    loop = _make_loop()
    loop._run_session_id = "run-current"
    loop._active_plan_state = {
        "run_id": "run-current",
        "plan_id": "plan-current",
        "plan_version": "v2",
        "summary": "Confirm the landing page works",
        "steps": [_make_step("step-1")],
    }
    loop.control_queue = SequenceQueue(
        [
            {"type": "confirmed", "run_id": "run-stale", "plan_id": "plan-stale", "plan_version": "v1"},
            {"type": "confirmed", "run_id": "run-current", "plan_id": "plan-current", "plan_version": "v2"},
        ]
    )

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send

    result = asyncio.run(loop._wait_for_plan_confirmation())

    assert loop.control_queue.get_count == 2
    assert len(sent_events) == 1
    rejection = sent_events[0]
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "STALE_CONFIRMATION"
    assert rejection["run_id"] == "run-stale"
    assert rejection["payload"]["rejection_code"] == "STALE_CONFIRMATION"
    assert rejection["payload"]["detail"]
    assert "run_id" in rejection["payload"]["detail"]
    assert rejection["payload"]["current_state"]["run_id"] == "run-current"
    assert rejection["payload"]["current_state"]["plan_id"] == "plan-current"
    assert rejection["payload"]["current_state"]["plan_version"] == "v2"
    assert result["confirmed"] is True
    assert result["answer"] == "confirmed"
    assert result["run_id"] == "run-current"
    assert result["plan_id"] == "plan-current"
    assert result["plan_version"] == "v2"


def test_previous_run_completion_state_does_not_complete_new_run() -> None:
    loop = _make_loop()
    loop._run_session_id = "run-old"
    loop._new_run_session_id = lambda: "run-new"
    loop._run_completion_requested = True
    loop._run_completed_emitted = True
    loop.plan_confirmed = True
    loop.current_steps = [_make_step("step-old")]
    loop.recorded_step_payloads = [{"step_id": "step-old"}]
    loop.code_update_payloads = [{"step_id": "step-old"}]
    loop._active_plan_state = {"run_id": "run-old", "plan_id": "plan-old", "steps": [_make_step("step-old")]}

    loop._reset_lifecycle_state([_make_step("step-new")])

    assert loop._run_completion_requested is False
    assert loop._run_completed_emitted is False
    assert loop.plan_confirmed is False
    assert loop.recorded_step_payloads == []
    assert loop.code_update_payloads == []
    assert loop._active_plan_state is None
    assert loop.current_steps == [_make_step("step-new")]
    assert loop._run_session_id == "run-new"


def test_previous_run_recovery_state_does_not_block_new_run() -> None:
    loop = _make_loop()
    loop._run_session_id = "run-old"
    loop._new_run_session_id = lambda: "run-new"
    loop.phase = "recovering"
    loop.phase_tracker.current_phase = "recovery"
    loop.pending_recovery = True
    loop.active_failed_step_id = "step-old"
    loop._pending_failure_followup = True
    loop.current_steps = [_make_step("step-old")]
    loop.step_state_by_id = {"step-old": _make_step("step-old")}
    loop._active_plan_state = {"run_id": "run-old", "plan_id": "plan-old", "steps": [_make_step("step-old")]}

    loop._reset_lifecycle_state([_make_step("step-new")])

    assert loop.phase == "planning"
    assert loop.phase_tracker.get_phase() == "idle"
    assert loop.pending_recovery is False
    assert loop.active_failed_step_id is None
    assert loop._pending_failure_followup is False
    assert loop.current_steps == [_make_step("step-new")]
    assert loop.step_state_by_id == {}
    assert loop._active_plan_state is None
    assert loop._run_session_id == "run-new"
