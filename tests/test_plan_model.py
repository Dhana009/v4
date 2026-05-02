from __future__ import annotations

import asyncio

from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.current_steps = []
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = "idle"
    loop.phase = "planning"
    loop.plan_confirmed = False
    loop._pending_failure_followup = False
    loop._awaiting_step_record = False
    return loop


def _make_source_step(intent: str, element_info: dict[str, object]) -> dict[str, object]:
    return {
        "id": "step-1",
        "intent": intent,
        "element_info": element_info,
    }


def _make_plan_payload(
    action: str,
    element_name: str,
    code: str,
    summary: str = "I will click the submit button",
) -> dict[str, object]:
    return {
        "summary": summary,
        "steps": [
            {
                "number": 1,
                "action": action,
                "element_name": element_name,
                "code": code,
            }
        ],
        "instruction": "Confirm to proceed",
    }


def test_click_intent_creates_child_operation_type_click() -> None:
    loop = _make_loop()
    step = _make_source_step(
        "Click the submit button",
        {"text": "Submit", "aria_label": "Submit"},
    )

    children = loop._build_planned_children(step, {"element_name": "Submit"})

    assert len(children) == 1
    child = children[0]
    assert child["operation_id"] == "op_1"
    assert child["type"] == "click"
    assert child["status"] == "planned"
    assert child["locator"] == 'get_by_label("Submit")'


def test_assertion_intent_creates_child_operation_type_assert() -> None:
    loop = _make_loop()
    step = _make_source_step(
        "Assert the success message is visible",
        {"text": "Success", "aria_label": "Success message"},
    )

    children = loop._build_planned_children(step, {"element_name": "Success message"})

    assert len(children) == 1
    child = children[0]
    assert child["operation_id"] == "op_1"
    assert child["type"] == "assert"
    assert child["status"] == "planned"
    assert child["locator"] == 'get_by_label("Success message")'


def test_fill_intent_creates_child_operation_type_fill() -> None:
    loop = _make_loop()
    step = _make_source_step(
        "Type the email address",
        {"placeholder": "Email address"},
    )

    children = loop._build_planned_children(step, {"element_name": "Email address"})

    assert len(children) == 1
    child = children[0]
    assert child["operation_id"] == "op_1"
    assert child["type"] == "fill"
    assert child["status"] == "planned"
    assert child["locator"] == 'get_by_placeholder("Email address")'


def test_unknown_intent_creates_child_operation_type_unknown() -> None:
    loop = _make_loop()
    step = _make_source_step("Review the page for issues", {"text": "Overview"})

    children = loop._build_planned_children(step, {"element_name": "Overview"})

    assert len(children) == 1
    child = children[0]
    assert child["operation_id"] == "op_1"
    assert child["type"] == "unknown"
    assert child["status"] == "planned"


def test_existing_plan_ready_fields_are_preserved() -> None:
    loop = _make_loop()
    loop.current_steps = [
        _make_source_step(
            "Click the submit button",
            {"text": "Submit", "aria_label": "Submit"},
        )
    ]
    payload = _make_plan_payload("click", "Submit", "await submit.click();")
    payload["steps"][0]["extra"] = "keep"

    augmented = loop._build_plan_ready_payload(payload)
    step = augmented["steps"][0]

    assert augmented["summary"] == "I will click the submit button"
    assert augmented["instruction"] == "Confirm to proceed"
    assert step["number"] == 1
    assert step["action"] == "click"
    assert step["element_name"] == "Submit"
    assert step["code"] == "await submit.click();"
    assert step["extra"] == "keep"
    assert step["step_id"] == "step-1"
    assert step["intent"] == "Click the submit button"
    assert step["status"] == "planned"


def test_children_field_is_added_without_breaking_existing_structure() -> None:
    loop = _make_loop()
    loop.current_steps = [
        _make_source_step(
            "Click the submit button",
            {"text": "Submit", "aria_label": "Submit"},
        )
    ]
    payload = _make_plan_payload("click", "Submit", "await submit.click();")

    augmented = loop._build_plan_ready_payload(payload)
    step = augmented["steps"][0]

    assert step["number"] == 1
    assert step["action"] == "click"
    assert step["element_name"] == "Submit"
    assert step["code"] == "await submit.click();"
    assert isinstance(step["children"], list)
    assert len(step["children"]) == 1
    assert step["children"][0]["type"] == "click"
    assert step["children"][0]["status"] == "planned"


def test_plan_ready_send_augments_payload_without_real_runtime() -> None:
    loop = _make_loop()
    loop.current_steps = [
        _make_source_step(
            "Click the submit button",
            {"text": "Submit", "aria_label": "Submit"},
        )
    ]
    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _make_plan_payload("click", "Submit", "await submit.click();"),
            }
        )
    )

    assert result["confirmed"] is True
    assert result["phase"] == "executing"
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert sent_messages[0][1]["summary"] == "I will click the submit button"
    assert sent_messages[0][1]["instruction"] == "Confirm to proceed"
    assert sent_messages[0][1]["steps"][0]["children"][0]["type"] == "click"
    assert sent_messages[0][1]["steps"][0]["children"][0]["status"] == "planned"
    assert loop.plan_confirmed is True
