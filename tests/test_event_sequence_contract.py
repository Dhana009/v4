from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

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
    return loop


def _make_step_context() -> dict[str, object]:
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


def test_step_recorded_is_blocked_before_plan_confirmation() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id

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

    assert result == {
        "sent": False,
        "blocked": True,
        "requires_confirmation": True,
        "reason": "step_recorded blocked before confirmed execution.",
    }
    assert sent_events == []


def test_step_recorded_is_followed_by_code_update_and_backend_owned_order() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
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
    assert loop._run_completion_requested is True
    step_event = sent_events[0]
    code_event = sent_events[1]
    run_completed_event = sent_events[2]
    assert step_event["children"][0]["operation_id"] == "op_1"
    assert step_event["children"][0]["code_lines"]
    assert code_event["step_id"] == "step-1"
    assert code_event["operation_id"] == "op_1"
    assert code_event["lines"] == step_event["children"][0]["code_lines"]
    assert run_completed_event["run_id"] == "run-test-001"
    assert run_completed_event["recorded_count"] == 1
    assert run_completed_event["skipped_count"] == 0


def test_failed_step_sets_recovery_state_before_terminal_resolution() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}

    loop._mark_step_failed(step_context, "boom")

    assert loop.pending_recovery is True
    assert loop.phase == "recovering"
    assert loop.phase_tracker.get_phase() == "recovery"
    assert loop.active_failed_step_id == "step-1"
    assert loop._all_steps_resolved() is False


def test_recovery_open_blocks_terminal_resolution() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    step_context["status"] = "recorded"
    loop.plan_confirmed = True
    loop._recording_steps = [step_context]
    loop.pending_recovery = True
    loop.active_failed_step_id = "step-1"

    assert loop._all_steps_resolved() is False

    loop.pending_recovery = False
    loop.active_failed_step_id = None

    assert loop._all_steps_resolved() is True


def test_stale_confirmation_does_not_execute_until_matching_run_context() -> None:
    loop = _make_loop()
    loop._run_session_id = "run-active"
    loop._remember_plan_review_context(
        {
            "run_id": "run-active",
            "plan_id": "plan-active",
            "summary": "Confirm the landing page works",
            "steps": [
                {
                    "step_id": "step-1",
                    "intent": "Check that Get started is visible and click it",
                }
            ],
        }
    )
    loop.control_queue = SequenceQueue(
        [
            {"type": "confirmed", "run_id": "run-stale", "plan_id": "plan-stale"},
            {"type": "confirmed", "run_id": "run-active", "plan_id": "plan-active"},
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
    assert rejection["payload"]["rejection_code"] == "STALE_CONFIRMATION"
    assert rejection["payload"]["current_state"]["run_id"] == "run-active"
    assert rejection["payload"]["current_state"]["plan_id"] == "plan-active"
    assert result["confirmed"] is True
    assert result["answer"] == "confirmed"
    assert result["run_id"] == "run-active"
    assert result["plan_id"] == "plan-active"
