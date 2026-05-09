from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


class QueueHarness:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = QueueHarness()
    loop.phase_tracker = PhaseTracker()
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
    loop._run_session_id = "run-test-001"
    loop.llm = SimpleNamespace(messages=[], system_prompt="", client=object(), reset=lambda: None)
    return loop


def _make_step_context() -> dict[str, object]:
    return {
        "step_id": "step-1",
        "step_number": 1,
        "intent": "Click the submit button",
        "element_info": {
            "text": "Submit",
            "attributes": {"aria-label": "Submit"},
        },
        "expected_outcome": {
            "type": "navigation",
            "description": "goes to docs intro page",
            "source": "user",
            "required": True,
        },
    }


def _install_server_stubs(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setattr(server.app.state, "active_run_session", None, raising=False)

    fake_queue = QueueHarness()

    async def fake_launch_browser() -> None:
        return None

    class FakeAgentLoop:
        def __init__(self, ws, control_queue) -> None:
            self.ws = ws
            self.control_queue = control_queue
            self.llm = SimpleNamespace(reset=lambda: None)
            self._run_session_id = "run-test-001"
            self.phase = "executing"
            self.last_plan_ready_payload = {
                "steps": [{"step_id": "step-1", "intent": "Check that Get started is visible and click it"}]
            }
            self.recorded_step_payloads = []

        async def run(self, steps) -> None:  # noqa: ARG002
            return None

        def _current_phase(self) -> str:
            return self.phase

        def _current_run_session_id(self) -> str:
            return self._run_session_id

        def _build_session_state_payload(self) -> dict[str, object]:
            return {
                "run_id": self._run_session_id,
                "phase": self.phase,
                "steps": list(self.last_plan_ready_payload.get("steps") or []),
                "recorded_steps": list(self.recorded_step_payloads),
            }

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)


def test_run_started_is_currently_a_backend_phase_checkpoint_not_a_typed_event() -> None:
    """
    Contract decision: run_started is currently represented as a backend-owned
    phase_tracker transition into planning with reason=run_started, not as a
    typed backend event envelope.
    """
    loop = _make_loop()

    transition = loop.phase_tracker.set_phase("planning", reason="run_started")

    assert transition is not None
    assert transition.from_phase == "idle"
    assert transition.to_phase == "planning"
    assert transition.reason == "run_started"
    assert transition.step_id == "none"
    assert loop.phase_tracker.get_phase() == "planning"


def test_execution_started_is_currently_mapped_to_backend_executing_phase_after_confirmation() -> None:
    """
    Contract decision: execution_started is currently mapped to the backend
    transition into executing after confirmation is accepted.
    """
    loop = _make_loop()
    loop.current_steps = [_make_step_context()]

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": {
                    "run_id": "run-test-001",
                    "summary": "Confirm the landing page works",
                    "steps": [{"step_id": "step-1", "intent": "Check that Get started is visible and click it"}],
                },
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert [event["type"] for event in sent_events] == ["plan_ready"]
    assert loop.phase == "executing"
    assert loop.phase_tracker.get_phase() == "executing"


def test_lifecycle_bridge_sequence_maps_execution_started_between_confirmation_and_recording() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    success_record = {
        "tool": "action_click",
        "action": "click",
        "locator": 'get_by_role("button", name="Submit")',
        "result": {"success": True, "skipped": False},
        "step_context": step_context,
        "action_context": {"locator": 'get_by_role("button", name="Submit")'},
        "tool_args": {"locator": 'get_by_role("button", name="Submit")'},
        "step_id": "step-1",
        "step_number": 1,
        "browser_state_before": {"url": "https://playwright.dev/", "title": "Playwright"},
        "browser_state_after": {"url": "https://playwright.dev/docs/intro", "title": "Installation | Playwright"},
    }
    loop.current_steps = [step_context]
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    planning_transition = loop.phase_tracker.set_phase("planning", reason="run_started")
    assert planning_transition is not None
    plan_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": {
                    "run_id": "run-test-001",
                    "summary": "Confirm the landing page works",
                    "steps": [{"step_id": "step-1", "intent": step_context["intent"]}],
                },
            }
        )
    )
    assert plan_result["phase"] == "executing"
    assert loop.phase_tracker.get_phase() == "executing"

    allowed = loop._validate_confirmed_execution_tool_call(
        "action_click",
        {"locator": 'get_by_label("Submit")'},
    )
    assert allowed["allowed"] is True
    success_record = loop._record_confirmed_execution_child_result(
        step_context,
        allowed["expected_child"],
        tool_name="action_click",
        args={"locator": 'get_by_label("Submit")'},
        result={
            "success": True,
            "skipped": False,
            "locator": 'get_by_label("Submit")',
        },
        status="success",
    )
    assert success_record is not None
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"step-1": success_record}
    loop.successful_actions_by_step_id = {"step-1": [success_record]}

    recorded = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "step_recorded",
                "payload": {"run_id": "run-test-001", "step_id": "step-1", "step_number": 1},
            }
        )
    )

    assert recorded["sent"] is True
    assert [event["type"] for event in sent_events] == ["plan_ready", "step_recorded", "code_update", "run_completed"]
    assert planning_transition.reason == "run_started"
    assert sent_events[0]["type"] == "plan_ready"
    assert plan_result["phase"] == "executing"
    assert sent_events[1]["type"] == "step_recorded"
    assert loop.phase_tracker.get_phase() == "completed"


def test_frontend_facing_lifecycle_mapping_remains_backend_owned_via_session_state(monkeypatch) -> None:
    _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            message = websocket.receive_json()

    assert message["type"] == "session_state"
    assert message["run_id"] == "run-test-001"
    assert message["phase"] == "executing"
    assert message["steps"] == [{"step_id": "step-1", "intent": "Check that Get started is visible and click it"}]
