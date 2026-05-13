from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server
from agent import AgentLoop
from runtime.deterministic_fast_path import classify_fast_path
from runtime.event_contracts import FRONTEND_COMMAND_SCHEMA_VERSION
from runtime.phase_tracker import PhaseTracker


class QueueHarness:
    def __init__(self, response: dict[str, object] | None = None) -> None:
        self.response = response
        self.items: list[dict[str, object]] = []
        self.get_count = 0

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)

    async def get(self) -> dict[str, object]:
        self.get_count += 1
        if self.response is not None:
            response = self.response
            self.response = None
            return response
        if not self.items:
            raise AssertionError("expected another backend event")
        return self.items.pop(0)


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = QueueHarness()
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
    loop.llm = SimpleNamespace(messages=[], system_prompt="", client=object(), reset=lambda: None)
    return loop


def _make_click_step_context() -> dict[str, object]:
    return {
        "step_id": "step-1",
        "step_number": 1,
        "intent": "Click the Get started button",
        "element_info": {
            "text": "Get started",
            "attributes": {"aria-label": "Get started"},
        },
        "element_name": "Get started",
        "locator": None,
        "status": "executing",
        "recorded": False,
        "last_error": None,
        "expected_outcome": {
            "type": "navigation",
            "description": "goes to docs intro page",
            "source": "user",
            "required": True,
        },
    }


def _make_click_success_record(step_context: dict[str, object]) -> dict[str, object]:
    locator = 'get_by_role("button", name="Get started")'
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


def _make_assertion_step_context() -> tuple[dict[str, object], str, str, str]:
    specific_target = "Playwright Test Agents"
    broad_page_text = "PLAYWRIGHT GUIDE / LOCAL DOCS Playwright Test Agents docs landing page"
    specific_locator = f'get_by_text("{specific_target}", exact=True)'
    step_context = _make_click_step_context()
    step_context["intent"] = f"Assert {specific_target} is visible"
    step_context["element_name"] = broad_page_text
    step_context["element_info"] = {
        "text": broad_page_text,
        "attributes": {"aria-label": broad_page_text},
    }
    step_context["locator"] = specific_locator
    return step_context, specific_target, broad_page_text, specific_locator


def _install_server_stubs(monkeypatch, *, phase: str = "planning", run_id: str = "run-test-001"):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setattr(server.app.state, "active_run_session", None, raising=False)

    fake_queue = QueueHarness()
    created: dict[str, object] = {}

    async def fake_launch_browser() -> None:
        return None

    class FakeAgentLoop:
        def __init__(self, ws, control_queue) -> None:
            self.ws = ws
            self.control_queue = control_queue
            self.phase = phase
            self._run_session_id = run_id
            self.llm = SimpleNamespace(reset=lambda: None)
            self.run_calls: list[list[dict[str, object]]] = []
            created["agent"] = self

        async def run(self, steps) -> None:  # noqa: ARG002
            self.run_calls.append(list(steps))
            return None

        def _current_phase(self) -> str:
            return self.phase

        def _current_run_session_id(self) -> str:
            return self._run_session_id

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    return fake_queue, created


def test_deterministic_click_golden_sequence_blocks_until_confirmation_and_then_records_in_order() -> None:
    loop = _make_loop()
    step_context = _make_click_step_context()
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

    blocked = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "step_recorded",
                "payload": {"run_id": "run-test-001", "step_id": "step-1", "step_number": 1},
            }
        )
    )
    assert blocked == {
        "sent": False,
        "blocked": True,
        "requires_confirmation": True,
        "reason": "step_recorded blocked before confirmed execution.",
    }
    assert sent_events == []

    plan_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                    "message_type": "plan_ready",
                    "payload": {
                        "run_id": "run-test-001",
                        "summary": "I will click the Get started button",
                        "steps": [{"step_id": "step-1", "intent": step_context["intent"]}],
                        "instruction": "Confirm to proceed",
                    },
            }
        )
    )
    assert plan_result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert [event["type"] for event in sent_events] == ["plan_ready"]

    allowed = loop._validate_confirmed_execution_tool_call(
        "action_click",
        {"locator": 'get_by_label("Get started")'},
    )
    assert allowed["allowed"] is True
    success_record = loop._record_confirmed_execution_child_result(
        step_context,
        allowed["expected_child"],
        tool_name="action_click",
        args={"locator": 'get_by_label("Get started")'},
        result={
            "success": True,
            "skipped": False,
            "locator": 'get_by_label("Get started")',
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
    assert [event["type"] for event in sent_events] == [
        "plan_ready",
        "step_recorded",
        "code_update",
        "run_completed",
    ]
    assert sent_events[1]["type"] == "step_recorded"
    assert sent_events[2]["type"] == "code_update"
    assert sent_events[3]["type"] == "run_completed"
    assert sent_events[2]["lines"] == [sent_events[1]["generated_line"]]
    assert sent_events[3]["recorded_count"] == 1


def test_deterministic_assertion_golden_sequence_preserves_specific_target_and_parent_metadata() -> None:
    loop = _make_loop()
    step_context, specific_target, broad_page_text, specific_locator = _make_assertion_step_context()
    expected_line = (
        f'await expect(page.getByText("{specific_target}", {{ exact: true }})).'
        f'toBeVisible();'
    )

    loop.current_steps = [step_context]
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "step-1"

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    plan_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": {
                    "run_id": "run-test-001",
                    "summary": f"Assert {specific_target} is visible",
                    "steps": [{"step_id": "step-1", "intent": step_context["intent"]}],
                },
            }
        )
    )
    assert plan_result["confirmed"] is True

    allowed = loop._validate_confirmed_execution_tool_call(
        "action_assert",
        {"locator": specific_locator, "assertion": "visible"},
    )
    assert allowed["allowed"] is True
    success_record = loop._record_confirmed_execution_child_result(
        step_context,
        allowed["expected_child"],
        tool_name="action_assert",
        args={"locator": specific_locator, "assertion": "visible"},
        result={
            "success": True,
            "skipped": False,
            "locator": specific_locator,
            "assertion": "visible",
        },
        status="success",
    )
    assert success_record is not None
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"step-1": success_record}
    loop.successful_actions_by_step_id = {"step-1": [success_record]}

    record_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "step_recorded",
                "payload": {"step_id": "step-1", "step_number": 1},
            }
        )
    )
    assert record_result["sent"] is True

    assert [event["type"] for event in sent_events] == [
        "plan_ready",
        "step_recorded",
        "code_update",
        "run_completed",
    ]
    step_recorded_payload = sent_events[1]
    code_update_payload = sent_events[2]
    recorded_child = step_recorded_payload["children"][0]
    assert step_recorded_payload["expected_outcome"] == step_context["expected_outcome"]
    assert recorded_child["target"] == specific_target
    assert recorded_child["locator"] == specific_locator
    assert recorded_child["code_lines"] == [expected_line]
    assert code_update_payload["lines"] == [expected_line]
    assert specific_target in code_update_payload["full_spec_preview"]
    assert broad_page_text not in code_update_payload["full_spec_preview"]


def test_runtime_rejection_golden_sequence_emits_only_runtime_rejected_without_success_events(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch, phase="planning", run_id="run-test-001")

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            initial_message = websocket.receive_json()
            assert initial_message["type"] in {"status", "ready"}

            websocket.send_json(
                {
                    "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
                    "command_id": "cmd-malformed-sequence",
                    "source": "frontend",
                    "payload": {"answer": "confirmed"},
                }
            )
            response = websocket.receive_json()

    assert response["type"] == "runtime_rejected"
    assert response["rejection_code"] == "MALFORMED_COMMAND"
    assert fake_queue.items == []
    assert created["agent"].run_calls == []
    assert response["type"] != "plan_ready"
    assert response["type"] != "step_recorded"
    assert response["type"] != "code_update"
    assert response["type"] != "run_completed"


def test_fake_llm_ambiguous_sequence_emits_plan_ready_before_execution_and_skips_fast_path() -> None:
    qualifies, reason = classify_fast_path(
        user_message="figure out what to do on this page",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason

    loop = _make_loop()
    step_context = _make_click_step_context()
    loop.current_steps = [step_context]
    sent_events: list[dict[str, object]] = []
    fake_model_calls = {"count": 0}

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": False, "correction": "Need clarification before executing"}

    async def fake_model_planning_round() -> dict[str, object]:
        fake_model_calls["count"] += 1
        return await loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": {
                    "run_id": "run-llm-001",
                    "summary": "I need clarification before acting on this page",
                    "steps": [{"step_id": "step-1", "intent": "Figure out what to do on this page"}],
                    "instruction": "Confirm to proceed",
                },
            }
        )

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(fake_model_planning_round())

    assert fake_model_calls["count"] == 1
    assert result["confirmed"] is False
    assert [event["type"] for event in sent_events] == ["plan_ready"]
    assert not any(event["type"] == "step_recorded" for event in sent_events)
    assert not any(event["type"] == "code_update" for event in sent_events)
    assert not any(event["type"] == "run_completed" for event in sent_events)
