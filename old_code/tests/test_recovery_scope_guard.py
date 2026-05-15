from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from agent import AgentLoop
from runtime.context_manager import ContextManager
from runtime.phase_tracker import PhaseTracker


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
    loop._plan_correction_pending = False
    loop.capability_gaps = []
    loop.recorded_step_payloads = []
    loop.code_update_payloads = []
    loop.replay_recorded_step_payloads_by_step_id = {}
    loop.replay_action_history_by_step_id = {}
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
    return loop


def _plan_ready_payload(summary: str) -> dict[str, object]:
    return {
        "summary": summary,
        "steps": [
            {
                "step_id": "step-1",
                "intent": "Check that Get started is visible",
                "children": [
                    {
                        "operation_id": "op_1",
                        "type": "assert",
                        "description": "Get started is visible",
                        "target": "Get started",
                        "locator": 'get_by_role("button", name="Get started")',
                        "status": "planned",
                        "code_lines": ["await expect(getStarted).toBeVisible();"],
                    }
                ],
            }
        ],
        "instruction": "Confirm to proceed",
    }


@pytest.mark.parametrize(
    ("pending_recovery", "active_failed_step_id", "pending_failure_followup"),
    [
        (True, None, False),
        (False, "step-1", False),
        (False, None, True),
    ],
)
def test_plan_ready_during_unresolved_recovery_is_blocked(
    pending_recovery: bool,
    active_failed_step_id: str | None,
    pending_failure_followup: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    loop = _make_loop()
    loop.phase = "recovering"
    loop.phase_tracker.current_phase = "recovery"
    loop.pending_recovery = pending_recovery
    loop.active_failed_step_id = active_failed_step_id
    loop._pending_failure_followup = pending_failure_followup
    loop.last_plan_ready_payload = {"summary": "Existing plan", "steps": [{"step_id": "old-step"}]}
    loop.last_plan_step_ids = ["old-step"]
    loop.last_plan_summary = "Existing plan"
    loop.last_plan_original_user_intent = "Existing intent"

    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(msg_type: str, **kwargs: object) -> None:
        sent_messages.append((msg_type, kwargs))

    async def fail_if_wait_called() -> dict[str, object]:
        raise AssertionError("plan_ready should not wait for confirmation when recovery is unresolved")

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fail_if_wait_called

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _plan_ready_payload("New plan summary"),
            }
        )
    )

    stdout = capsys.readouterr().out
    assert "[RECOVERY_SCOPE_GUARD] blocked plan_ready during unresolved recovery step_id=" in stdout
    if active_failed_step_id:
        assert f"step_id={active_failed_step_id}" in stdout

    assert result == {
        "sent": False,
        "blocked": True,
        "reason": "plan_ready_blocked_during_recovery",
        "message": "Recovery is unresolved. Completed steps are locked; retry, skip, stop, or ask about the failed step only.",
    }
    assert sent_messages == []
    assert loop.last_plan_ready_payload == {"summary": "Existing plan", "steps": [{"step_id": "old-step"}]}
    assert loop.last_plan_step_ids == ["old-step"]
    assert loop.last_plan_summary == "Existing plan"
    assert loop.last_plan_original_user_intent == "Existing intent"
    assert loop.phase == "recovering"
    assert loop.phase_tracker.get_phase() == "recovery"
    assert loop.pending_recovery is pending_recovery
    assert loop.active_failed_step_id == active_failed_step_id
    assert loop._pending_failure_followup is pending_failure_followup


def test_plan_ready_outside_recovery_still_works() -> None:
    loop = _make_loop()
    loop.phase = "planning"
    loop.phase_tracker.current_phase = "planning"
    loop.last_plan_ready_payload = None

    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(msg_type: str, **kwargs: object) -> None:
        sent_messages.append((msg_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _plan_ready_payload("Visible and click"),
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert sent_messages and sent_messages[0][0] == "plan_ready"
    assert sent_messages[0][1]["summary"] == "Visible and click"
    steps = sent_messages[0][1]["steps"]
    assert isinstance(steps, list)
    assert len(steps) == 1
    assert isinstance(steps[0], dict)
    assert steps[0].get("intent") == "Check that Get started is visible"
    assert loop.plan_confirmed is True
    assert loop.phase == "executing"
    assert loop.phase_tracker.get_phase() == "executing"


def test_recovery_context_instruction_locks_completed_steps() -> None:
    bundle = ContextManager().prepare_messages(
        [],
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"phase": "recovery"},
    )

    system_messages = [message for message in bundle.messages if isinstance(message, dict) and message.get("role") == "system"]
    assert system_messages
    instruction = "\n".join(str(message.get("content") or "") for message in system_messages)

    assert "Completed/recorded steps are locked." in instruction
    assert "Do not replan completed steps." in instruction
    assert "Do not send plan_ready during unresolved recovery." in instruction
    assert "Work only on the failed unresolved step." in instruction
    assert "Allowed outcomes: retry or repair the failed step, ask user, skip, stop/end." in instruction
