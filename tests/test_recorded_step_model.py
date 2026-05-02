from __future__ import annotations

import asyncio

from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = object()
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = "idle"
    loop.phase = "planning"
    loop.plan_confirmed = True
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
    loop._awaiting_step_record = True
    loop._pending_failure_followup = False
    loop._run_completion_requested = False
    loop.run_stop_requested = False
    loop._llm_call_counter = 0
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
        "element_name": "Submit",
        "locator": None,
        "status": "executing",
        "recorded": False,
        "last_error": None,
    }


def _make_action_record(
    step_context: dict[str, object],
    tool_name: str,
    action: str,
    locator: str,
    assertion: str | None = None,
) -> dict[str, object]:
    return {
        "tool": tool_name,
        "action": action,
        "locator": locator,
        "result": {"success": True, "skipped": False},
        "step_context": step_context,
        "action_context": {
            "locator": locator,
            **({"assertion": assertion} if assertion is not None else {}),
        },
        "tool_args": {
            "locator": locator,
            **({"assertion": assertion} if assertion is not None else {}),
        },
        "step_id": step_context["step_id"],
        "step_number": step_context["step_number"],
    }


def _make_success_record(step_context: dict[str, object]) -> dict[str, object]:
    locator = 'get_by_role("button", name="Submit")'
    return _make_action_record(step_context, "action_click", "click", locator)


def _make_assert_success_record(step_context: dict[str, object]) -> dict[str, object]:
    locator = 'get_by_label("Get started")'
    return _make_action_record(
        step_context,
        "action_assert",
        "assert",
        locator,
        assertion="visible",
    )


def test_step_recorded_payload_adds_parent_child_model_and_preserves_flat_fields() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    success_record = _make_success_record(step_context)
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"step-1": success_record}

    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "step_recorded",
                "payload": {
                    "step_id": "step-1",
                    "step_number": 1,
                },
            }
        )
    )

    assert result["sent"] is True
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[1][0] == "code_update"

    payload = sent_messages[0][1]
    children = payload["children"]
    child = children[0]
    code_update_payload = sent_messages[1][1]

    assert payload["step_id"] == "step-1"
    assert payload["step_number"] == 1
    assert payload["action"] == "click"
    assert payload["element_name"] == "Submit"
    assert payload["locator"] == 'get_by_role("button", name="Submit")'
    assert payload["status"] == "success"
    assert payload["intent"] == "Click the submit button"
    assert isinstance(children, list)
    assert len(children) == 1
    assert child["operation_id"] == "op_1"
    assert child["type"] == "click"
    assert child["status"] == "success"
    assert child["code_lines"] == [payload["generated_line"]]
    assert code_update_payload["step_id"] == "step-1"
    assert code_update_payload["operation_id"] == "op_1"
    assert code_update_payload["lines"] == [payload["generated_line"]]
    assert code_update_payload["full_spec_preview"] == payload["generated_line"]
    assert isinstance(code_update_payload["diagnostics"], list)
    assert code_update_payload["diagnostics"] == []


def test_step_recorded_payload_uses_ordered_action_history_for_children() -> None:
    loop = _make_loop()
    step_context = {
        "step_id": "step-1",
        "step_number": 1,
        "intent": "Check that Get started is visible and click it",
        "element_info": {
            "text": "Get started",
            "attributes": {"aria-label": "Get started"},
        },
        "element_name": "Get started",
        "locator": None,
        "status": "executing",
        "recorded": False,
        "last_error": None,
    }
    assert_record = _make_assert_success_record(step_context)
    click_record = _make_action_record(
        step_context,
        "action_click",
        "click",
        'get_by_label("Get started")',
    )
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.last_successful_action = click_record
    loop.successful_action_by_step_id = {"step-1": click_record}
    loop.successful_actions_by_step_id = {"step-1": [assert_record, click_record]}

    payload = loop._build_step_record_payload(
        {
            "step_id": "step-1",
            "step_number": 1,
        },
        step_context,
    )

    assert payload["step_id"] == "step-1"
    assert payload["step_number"] == 1
    assert payload["action"] == "click"
    assert payload["element_name"] == "Get started"
    assert payload["locator"] == 'get_by_label("Get started")'
    assert payload["status"] == "success"
    assert payload["intent"] == "Check that Get started is visible and click it"

    children = payload["children"]
    assert isinstance(children, list)
    assert len(children) == 2

    assert_child = children[0]
    click_child = children[1]
    assert_line = loop._build_generated_line(
        "assert",
        'get_by_label("Get started")',
        {"locator": 'get_by_label("Get started")', "assertion": "visible"},
    )
    click_line = loop._build_generated_line(
        "click",
        'get_by_label("Get started")',
        {"locator": 'get_by_label("Get started")'},
    )

    assert assert_child["operation_id"] == "op_1"
    assert assert_child["type"] == "assert"
    assert assert_child["status"] == "success"
    assert assert_child["code_lines"] == [assert_line]
    assert click_child["operation_id"] == "op_2"
    assert click_child["type"] == "click"
    assert click_child["status"] == "success"
    assert click_child["code_lines"] == [click_line]
