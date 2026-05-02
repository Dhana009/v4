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


def _make_step_context(expected_outcome: dict[str, object] | None = None) -> dict[str, object]:
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
        "expected_outcome": expected_outcome
        or {
            "type": "navigation",
            "description": "goes to docs intro page",
            "source": "user",
            "required": True,
        },
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
    success_record["browser_state_before"] = {
        "url": "https://playwright.dev/",
        "title": "Playwright",
    }
    success_record["browser_state_after"] = {
        "url": "https://playwright.dev/docs/intro",
        "title": "Installation | Playwright",
    }
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
    assert payload["observed_outcome"] == {
        "type": "navigation",
        "before_url": "https://playwright.dev/",
        "after_url": "https://playwright.dev/docs/intro",
        "before_title": "Playwright",
        "after_title": "Installation | Playwright",
        "matched_expected": True,
    }
    assert payload["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    assert isinstance(children, list)
    assert len(children) == 1
    assert child["operation_id"] == "op_1"
    assert child["type"] == "click"
    assert child["status"] == "success"
    assert child["code_lines"] == [payload["generated_line"]]
    assert "expected_outcome" not in child
    assert "observed_outcome" not in child
    assert code_update_payload["step_id"] == "step-1"
    assert code_update_payload["operation_id"] == "op_1"
    assert code_update_payload["lines"] == [payload["generated_line"]]
    assert code_update_payload["full_spec_preview"] == payload["generated_line"]
    assert isinstance(code_update_payload["diagnostics"], list)
    assert code_update_payload["diagnostics"] == []


def test_step_recorded_payload_records_no_visible_change_without_expected_outcome() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    step_context.pop("expected_outcome", None)
    success_record = _make_success_record(step_context)
    success_record["browser_state_before"] = {
        "url": "https://playwright.dev/docs/intro",
        "title": "Installation | Playwright",
    }
    success_record["browser_state_after"] = {
        "url": "https://playwright.dev/docs/intro",
        "title": "Installation | Playwright",
    }
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"step-1": success_record}
    loop.successful_actions_by_step_id = {"step-1": [success_record]}

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
    payload = sent_messages[0][1]
    assert payload["observed_outcome"] == {
        "type": "no_visible_change",
        "before_url": "https://playwright.dev/docs/intro",
        "after_url": "https://playwright.dev/docs/intro",
        "before_title": "Installation | Playwright",
        "after_title": "Installation | Playwright",
        "matched_expected": None,
    }
    assert "expected_outcome" not in payload


def test_step_recorded_payload_leaves_matched_expected_null_for_not_sure_expected_outcome() -> None:
    loop = _make_loop()
    step_context = _make_step_context(
        expected_outcome={
            "type": "not_sure",
            "description": "not sure",
            "source": "user",
            "required": False,
        }
    )
    success_record = _make_success_record(step_context)
    success_record["browser_state_before"] = {
        "url": "https://playwright.dev/",
        "title": "Playwright",
    }
    success_record["browser_state_after"] = {
        "url": "https://playwright.dev/docs/intro",
        "title": "Installation | Playwright",
    }
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"step-1": success_record}
    loop.successful_actions_by_step_id = {"step-1": [success_record]}

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
    payload = sent_messages[0][1]
    assert payload["observed_outcome"] == {
        "type": "navigation",
        "before_url": "https://playwright.dev/",
        "after_url": "https://playwright.dev/docs/intro",
        "before_title": "Playwright",
        "after_title": "Installation | Playwright",
        "matched_expected": None,
    }
    assert payload["expected_outcome"] == {
        "type": "not_sure",
        "description": "not sure",
        "source": "user",
        "required": True,
    }


def test_step_recorded_payload_preserves_spaces_and_canonical_step_id() -> None:
    loop = _make_loop()
    step_context = {
        "step_id": "pending-step-mooeb8ca-2",
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
        "expected_outcome": {
            "type": "navigation",
            "description": "thus assertion on the new page after clicking the button",
            "source": "user",
            "required": True,
        },
    }
    success_record = _make_success_record(step_context)
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"pending-step-mooeb8ca-2": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"pending-step-mooeb8ca-2": success_record}
    loop.successful_actions_by_step_id = {"pending-step-mooeb8ca-2": [success_record]}

    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "step_recorded",
                "payload": {
                    "step_id": "1",
                    "step_number": 1,
                },
            }
        )
    )

    assert result["sent"] is True
    assert len(sent_messages) == 2
    payload = sent_messages[0][1]
    assert payload["step_id"] == "pending-step-mooeb8ca-2"
    assert payload["expected_outcome"] == {
        "type": "navigation",
        "description": "thus assertion on the new page after clicking the button",
        "source": "user",
        "required": True,
    }
    assert sent_messages[1][0] == "code_update"


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
        "expected_outcome": {
            "type": "navigation",
            "description": "goes to docs intro page",
            "source": "user",
            "required": True,
        },
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
    assert payload["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }

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
    assert assert_child["description"] == "Get started is visible"
    assert assert_child["code_lines"] == [assert_line]
    assert "expected_outcome" not in assert_child
    assert click_child["operation_id"] == "op_2"
    assert click_child["type"] == "click"
    assert click_child["status"] == "success"
    assert click_child["description"] == "Get started"
    assert click_child["code_lines"] == [click_line]
    assert "expected_outcome" not in click_child


def test_auto_recorded_step_is_archived_and_replayable() -> None:
    loop = _make_loop()
    step_context = {
        "step_id": "pending-step-mooeb8ca-2",
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
        "expected_outcome": {
            "type": "navigation",
            "description": "thus assertion on the new page after clicking the button",
            "source": "user",
            "required": True,
        },
    }
    success_record = _make_success_record(step_context)
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"pending-step-mooeb8ca-2": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "pending-step-mooeb8ca-2"
    loop.plan_confirmed = True
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"pending-step-mooeb8ca-2": success_record}
    loop.successful_actions_by_step_id = {"pending-step-mooeb8ca-2": [success_record]}
    loop.replay_action_history_by_step_id = {"pending-step-mooeb8ca-2": [success_record]}
    loop._awaiting_step_record = True

    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    auto_recorded_payload = asyncio.run(loop._auto_record_successful_step())

    assert auto_recorded_payload is not None
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[1][0] == "code_update"

    recorded_payload = sent_messages[0][1]
    assert recorded_payload["step_id"] == "pending-step-mooeb8ca-2"
    assert recorded_payload["expected_outcome"] == {
        "type": "navigation",
        "description": "thus assertion on the new page after clicking the button",
        "source": "user",
        "required": True,
    }
    assert loop.replay_recorded_step_payloads_by_step_id["pending-step-mooeb8ca-2"]["step_id"] == "pending-step-mooeb8ca-2"

    executed_actions: list[str] = []

    async def fake_click(args: dict[str, object]) -> dict[str, object]:
        executed_actions.append("click")
        assert str(args.get("locator") or "") == 'get_by_role("button", name="Submit")'
        return {"success": True, "error": None}

    loop._tool_action_click = fake_click

    replay_result = asyncio.run(loop.replay_one("pending-step-mooeb8ca-2"))

    assert replay_result == {
        "type": "replay_one_result",
        "ok": True,
        "step_id": "pending-step-mooeb8ca-2",
        "status": "success",
        "operation_count": 1,
    }
    assert executed_actions == ["click"]
