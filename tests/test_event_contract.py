from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import server
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


class FakeQueue:
    def __init__(self, response: dict[str, object] | None = None) -> None:
        self.response = response
        self.items: list[dict[str, object]] = []
        self.get_count = 0

    async def get(self) -> dict[str, object]:
        self.get_count += 1
        if self.response is not None:
            response = self.response
            self.response = None
            return response
        return {}

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = FakeQueue()
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
    loop._active_plan_state = None
    loop._active_plan_correction_state = None
    loop._plan_correction_pending = False
    loop._run_completion_requested = False
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
    return loop


def _make_plan_step_context() -> dict[str, object]:
    return {
        "step_id": "step-1",
        "step_number": 1,
        "intent": "Check that Get started is visible and click it",
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
        "browser_state_before": {
            "url": "https://playwright.dev/",
            "title": "Playwright",
        },
        "browser_state_after": {
            "url": "https://playwright.dev/docs/intro",
            "title": "Installation | Playwright",
        },
    }


def _install_server_stubs(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    fake_queue = FakeQueue()
    created: dict[str, object] = {}

    async def fake_launch_browser() -> None:
        return None

    class FakeAgentLoop:
        def __init__(self, ws, control_queue) -> None:
            self.ws = ws
            self.control_queue = control_queue
            self.llm = SimpleNamespace(reset=lambda: None)
            created["agent"] = self

        async def run(self, steps) -> None:  # noqa: ARG002
            return None

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    return fake_queue, created


def test_plan_ready_event_emits_explicit_step_tree_and_child_operation_ids() -> None:
    loop = _make_loop()
    loop.current_steps = [_make_plan_step_context()]

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
                    "steps": [
                        {
                            "step_id": "step-1",
                            "intent": "Check that Get started is visible and click it",
                        }
                    ],
                    "instruction": "Confirm to proceed",
                },
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_events) == 1
    plan_event = sent_events[0]
    assert plan_event["type"] == "plan_ready"
    assert plan_event["run_id"] == "run-test-001"
    assert plan_event["summary"] == "Confirm the landing page works"
    assert plan_event["steps"][0]["type"] == "step"
    assert plan_event["steps"][0]["kind"] == "step"
    assert plan_event["steps"][0]["step_id"] == "step-1"
    assert plan_event["steps"][0]["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    assert plan_event["steps"][0]["children"][0]["operation_id"] == "op_1"
    assert plan_event["steps"][0]["children"][0]["type"] == "assert"
    assert plan_event["steps"][0]["children"][1]["operation_id"] == "op_2"
    assert plan_event["steps"][0]["children"][1]["type"] == "click"


def test_step_recorded_event_emits_explicit_step_id_child_operation_id_and_code_update() -> None:
    loop = _make_loop()
    step_context = _make_plan_step_context()
    success_record = _make_success_record(step_context)
    loop.plan_confirmed = True
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"step-1": success_record}
    loop.successful_actions_by_step_id = {"step-1": [success_record]}

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "step_recorded",
                "payload": {
                    "run_id": "run-test-001",
                    "step_id": "step-1",
                    "step_number": 1,
                },
            }
        )
    )

    assert result["sent"] is True
    assert [event["type"] for event in sent_events] == ["step_recorded", "code_update", "run_completed"]
    step_event = sent_events[0]
    code_event = sent_events[1]
    run_completed_event = sent_events[2]
    assert step_event["type"] == "step_recorded"
    assert step_event["step_id"] == "step-1"
    assert step_event["step_number"] == 1
    assert step_event["action"] == "click"
    assert step_event["observed_outcome"] == {
        "type": "navigation",
        "before_url": "https://playwright.dev/",
        "after_url": "https://playwright.dev/docs/intro",
        "before_title": "Playwright",
        "after_title": "Installation | Playwright",
        "matched_expected": True,
    }
    assert step_event["children"][0]["operation_id"] == "op_1"
    assert step_event["children"][0]["code_lines"]
    assert code_event["type"] == "code_update"
    assert code_event["step_id"] == "step-1"
    assert code_event["operation_id"] == "op_1"
    assert code_event["lines"] == step_event["children"][0]["code_lines"]
    assert code_event["full_spec_preview"] == step_event["children"][0]["code_lines"][0]
    assert code_event["diagnostics"] == []
    assert run_completed_event["type"] == "run_completed"
    assert run_completed_event["run_id"] == "run-test-001"
    assert run_completed_event["recorded_count"] == 1
    assert run_completed_event["skipped_count"] == 0
    assert run_completed_event["summary"]


def test_clarification_needed_event_emits_question_and_options() -> None:
    loop = _make_loop()
    loop.control_queue = FakeQueue({"type": "option_selected", "answer": "Keep going"})

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send

    result = asyncio.run(
        loop._tool_ask_user(
            {
                "question": "What should I do?",
                "options": ["retry", "skip"],
            }
        )
    )

    assert result == {"answer": "Keep going", "event_type": "option_selected", "success": True}
    assert len(sent_events) == 1
    clarification_event = sent_events[0]
    assert clarification_event["type"] == "clarification_needed"
    assert clarification_event["question"] == "What should I do?"
    assert clarification_event["options"] == ["retry", "skip"]


def test_plan_ready_blocked_during_recovery_returns_a_user_friendly_rejection() -> None:
    loop = _make_loop()
    loop.pending_recovery = True
    loop.active_failed_step_id = "step-1"

    async def fake_send(message_type: str, **kwargs: object) -> None:  # noqa: ARG001
        raise AssertionError("blocked plan_ready should not reach the websocket")

    loop._send = fake_send

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

    assert result == {
        "sent": False,
        "blocked": True,
        "reason": "plan_ready_blocked_during_recovery",
        "message": "Recovery is unresolved. Completed steps are locked; retry, skip, stop, or ask about the failed step only.",
    }


def test_runtime_rejected_shape_is_explicit_and_renderable(monkeypatch) -> None:
    fake_queue, _created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json(
                {
                    "type": "replay_step",
                    "command_id": "cmd-1",
                    "step_id": "step-1",
                }
            )
            response = websocket.receive_json()

    assert response["type"] == "runtime_rejected"
    assert response["schema_version"].startswith("autoworkbench")
    assert response["command_id"] == "cmd-1"
    assert response["message"]
    assert response["current_state"]
    assert fake_queue.items == []


def test_run_completed_shape_is_explicit() -> None:
    loop = _make_loop()
    step_context = _make_plan_step_context()
    success_record = _make_success_record(step_context)
    loop.plan_confirmed = True
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"step-1": success_record}
    loop.successful_actions_by_step_id = {"step-1": [success_record]}

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send
    asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "step_recorded",
                "payload": {
                    "run_id": "run-test-001",
                    "step_id": "step-1",
                    "step_number": 1,
                },
            }
        )
    )

    assert any(event["type"] == "run_completed" for event in sent_events)
    run_completed_event = next(event for event in sent_events if event["type"] == "run_completed")
    assert run_completed_event["run_id"] == "run-test-001"
    assert run_completed_event["summary"]
    assert run_completed_event["recorded_count"] == 1
    assert run_completed_event["skipped_count"] == 0


def test_recovery_needed_shape_is_explicit() -> None:
    loop = _make_loop()
    step_context = _make_plan_step_context()
    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send
    loop._mark_step_failed(step_context, "boom")

    assert any(event["type"] == "recovery_needed" for event in sent_events)
    recovery_event = next(event for event in sent_events if event["type"] == "recovery_needed")
    assert recovery_event["step_id"] == "step-1"
    assert recovery_event["current_url"]
    assert recovery_event["error_summary"]
    assert recovery_event["tried"]


@pytest.mark.xfail(strict=True, reason="session_state typed event is not emitted on websocket reconnect yet")
def test_session_state_shape_is_explicit(monkeypatch) -> None:
    _fake_queue, _created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            message = websocket.receive_json()

    assert message["type"] == "session_state"
    assert message["run_id"] == "run-test-001"
    assert message["phase"]
    assert message["steps"]
    assert message["recorded_steps"]
