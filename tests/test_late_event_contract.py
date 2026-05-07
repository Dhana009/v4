from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from agent import AgentLoop
from runtime.event_contracts import normalize_frontend_command
from runtime.phase_tracker import PhaseTracker


class SequenceQueue:
    def __init__(self, messages: list[dict[str, object]] | None = None) -> None:
        self.messages = list(messages or [])
        self.get_count = 0

    async def get(self) -> dict[str, object]:
        self.get_count += 1
        if not self.messages:
            raise AssertionError("expected another backend event")
        return self.messages.pop(0)

    async def put(self, item: dict[str, object]) -> None:  # noqa: ARG002
        return None


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.control_queue = SequenceQueue()
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = "idle"
    loop.phase = "planning"
    loop._run_session_id = "run-current"
    loop._run_completion_requested = False
    loop._run_completed_emitted = False
    loop._recording_steps = []
    loop.last_plan_summary = "Run completed"
    loop.last_plan_ready_payload = None
    loop._active_plan_state = None
    loop.pending_recovery = False
    loop.active_failed_step_id = None
    loop._pending_failure_followup = False
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


def test_run_completed_event_is_emitted_only_once_for_same_run() -> None:
    loop = _make_loop()
    loop._run_completion_requested = True
    loop._recording_steps = [{"status": "recorded"}, {"status": "skipped"}]

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send

    asyncio.run(loop._emit_run_completed_event({"run_id": "run-current"}, {"run_id": "run-current"}))
    asyncio.run(loop._emit_run_completed_event({"run_id": "run-current"}, {"run_id": "run-current"}))

    assert [event["type"] for event in sent_events] == ["run_completed"]
    assert sent_events[0]["run_id"] == "run-current"
    assert sent_events[0]["recorded_count"] == 1
    assert sent_events[0]["skipped_count"] == 1


@pytest.mark.xfail(strict=True, reason="late confirmations are still accepted after the active plan context has been cleared")
def test_completed_run_rejects_late_confirmation_and_does_not_reopen_plan() -> None:
    loop = _make_loop()
    loop.phase = "completed"
    loop.phase_tracker.current_phase = "completed"
    loop._run_completed_emitted = True
    loop._run_completion_requested = False
    loop.control_queue = SequenceQueue(
        [{"type": "confirmed", "run_id": "run-completed", "plan_id": "plan-completed"}]
    )

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send

    result = asyncio.run(loop._wait_for_plan_confirmation())

    assert len(sent_events) == 1
    rejection = sent_events[0]
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "STALE_CONFIRMATION"
    assert rejection["run_id"] == "run-completed"
    assert rejection["payload"]["current_state"]["run_id"] == "run-completed"
    assert result["confirmed"] is False


@pytest.mark.xfail(strict=True, reason="stale correction commands still return a correction result instead of rejection")
def test_stale_correction_command_for_old_run_cannot_mutate_current_run() -> None:
    loop = _make_loop()
    loop._active_plan_state = {
        "run_id": "run-current",
        "plan_id": "plan-current",
        "plan_version": "v2",
        "summary": "Keep the newer run active",
        "steps": [_make_step("step-1")],
    }
    loop.control_queue = SequenceQueue(
        [
            {
                "type": "correction",
                "run_id": "run-old",
                "plan_id": "plan-old",
                "message": "Use the newer plan",
            }
        ]
    )

    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send

    result = asyncio.run(loop._wait_for_plan_confirmation())

    assert len(sent_events) == 1
    rejection = sent_events[0]
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "STALE_CONFIRMATION"
    assert rejection["run_id"] == "run-old"
    assert rejection["payload"]["current_state"]["run_id"] == "run-current"
    assert result["confirmed"] is False


@pytest.mark.parametrize(
    ("command_type", "payload"),
    [
        ("confirmed", {}),
        ("correction", {"message": "Use the newer plan"}),
    ],
)
@pytest.mark.xfail(strict=True, reason="normalize_frontend_command does not yet reject stale run_id mismatches")
def test_stale_command_with_run_id_mismatch_is_typed_rejected(
    command_type: str,
    payload: dict[str, object],
) -> None:
    command = {
        "type": command_type,
        "schema_version": "autoworkbench.command.v1",
        "command_id": f"cmd-{command_type}",
        "run_id": "run-old",
        "plan_id": "plan-old",
        **payload,
    }
    current_state = {
        "run_id": "run-current",
        "plan_id": "plan-current",
        "phase": "executing",
    }

    normalized_command, rejection = normalize_frontend_command(command, current_state=current_state)

    assert normalized_command is None
    assert rejection is not None
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "STALE_COMMAND"
    assert rejection["run_id"] == "run-old"
    assert rejection["command_id"] == f"cmd-{command_type}"
    assert rejection["current_state"]["run_id"] == "run-current"
    assert rejection["current_state"]["plan_id"] == "plan-current"
    assert "run_id" in rejection["detail"]
