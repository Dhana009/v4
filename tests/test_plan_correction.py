from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

import agent as agent_module
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker
from runtime.tool_registry import filter_tools_for_phase

OUTCOME_LIKE_LABELS = [
    "navigation",
    "modal",
    "dropdown",
    "new_tab",
    "toast_or_message",
    "content_change",
    "download",
    "file_picker",
    "no_visible_change",
    "not_sure",
]


def _make_current_step(
    intent: str = "Check that Get started is visible and click it",
    expected_outcome: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": "step-1",
        "intent": intent,
        "element_info": {
            "text": "Get started",
            "attributes": {"aria-label": "Get started"},
        },
        "expected_outcome": expected_outcome
        or {
            "type": "navigation",
            "description": "goes to docs intro page",
            "source": "user",
            "required": True,
        },
    }


def _make_plan_payload(step_specs: list[dict[str, object]], summary: str) -> dict[str, object]:
    return {
        "summary": summary,
        "steps": step_specs,
        "instruction": "Confirm to proceed",
    }


def _make_operation(
    operation_id: str,
    operation_type: str,
    description: str,
    target: str = "Get started",
    locator: str = 'get_by_label("Get started")',
    assertion: str | None = None,
    value: str | None = None,
) -> dict[str, object]:
    operation = {
        "operation_id": operation_id,
        "type": operation_type,
        "description": description,
        "target": target,
        "locator": locator,
        "status": "planned",
    }
    if assertion is not None:
        operation["assertion"] = assertion
    if value is not None:
        operation["value"] = value
    return operation


def _make_active_plan_state(
    intent: str,
    operations: list[dict[str, object]],
    summary: str = "I will click Get started",
    plan_id: str = "plan-1",
    step_id: str = "step-1",
) -> dict[str, object]:
    return {
        "plan_id": plan_id,
        "summary": summary,
        "original_user_intent": intent,
        "step_ids": [step_id],
        "target_step_id": step_id,
        "steps": [
            {
                "step_id": step_id,
                "intent": intent,
                "status": "planned",
                "children": operations,
            }
        ],
    }


def _make_tool_call(
    call_id: str,
    payload: dict[str, object],
    message_type: str = "plan_ready",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="send_to_overlay",
            arguments=json.dumps(
                {
                    "message_type": message_type,
                    "payload": payload,
                }
            ),
        ),
    )


def _make_ask_user_tool_call(call_id: str, question: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="ask_user",
            arguments=json.dumps({"question": question}),
        ),
    )


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
    loop._active_plan_state = None
    loop._active_plan_correction_state = None
    loop._run_completion_requested = False
    loop.run_stop_requested = False
    loop._llm_call_counter = 0
    loop.confirmed_plan_by_step_id = {}
    loop.confirmed_plan_step_ids = []
    loop.confirmed_child_results_by_step_id = {}
    loop.confirmed_execution_mismatch_count_by_step_id = {}
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
    loop._format_steps = lambda steps: "steps"
    return loop


def _install_common_run_stubs(loop: AgentLoop, sent_messages: list[tuple[str, dict[str, object]]]) -> None:
    def fake_reset_lifecycle_state(steps=None):
        loop.phase = "planning"
        loop.plan_confirmed = False
        loop.current_steps = list(steps or [])
        loop.phase_tracker.current_phase = "idle"
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
        loop.confirmed_plan_by_step_id = {}
        loop.confirmed_plan_step_ids = []
        loop.confirmed_child_results_by_step_id = {}
        loop.confirmed_execution_mismatch_count_by_step_id = {}
        loop._clear_plan_review_context()
        loop._clear_active_plan_state()
        loop._run_completion_requested = False
        loop.run_stop_requested = False
        loop._llm_call_counter = 0

    async def fake_send(msg_type, **kwargs):
        sent_messages.append((msg_type, kwargs))

    loop._reset_lifecycle_state = fake_reset_lifecycle_state
    loop._prepare_recording_steps = lambda steps: None
    loop._load_skills_for_steps = lambda steps: (["core"], "", [{"name": "core"}])
    loop._load_phase_skill_expansion = lambda phase: []
    loop._send = fake_send


def _plan_ready_response(call_id: str, step_specs: list[dict[str, object]], summary: str) -> SimpleNamespace:
    tool_call = _make_tool_call(call_id, _make_plan_payload(step_specs, summary))
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="", tool_calls=[tool_call])
            )
        ]
    )


def _plan_correction_diff_response(
    call_id: str,
    diff_payload: dict[str, object],
) -> SimpleNamespace:
    tool_call = _make_tool_call(call_id, diff_payload, message_type="plan_correction_diff")
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="", tool_calls=[tool_call])
            )
        ]
    )


def _final_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text, tool_calls=[])
            )
        ]
    )


class _QueuedEvents:
    def __init__(self, events: list[dict[str, object]]) -> None:
        self._events = list(events)

    async def get(self) -> dict[str, object]:
        if not self._events:
            raise AssertionError("unexpected control queue get")
        return self._events.pop(0)


def _make_waiting_correction_state(loop: AgentLoop) -> dict[str, object]:
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    active_plan["steps"][0]["expected_outcome"] = {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    correction_state["retry_count"] = 2
    correction_state["needs_clarification"] = True
    correction_state["clarification_question"] = "Should I keep the click and add an assertion before it?"
    correction_state["last_validation_feedback"] = correction_state["clarification_question"]
    loop._active_plan_correction_state = correction_state
    return correction_state


def test_plan_correction_message_uses_active_plan_context() -> None:
    loop = _make_loop()
    loop.current_steps = [_make_current_step()]
    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {
            "confirmed": False,
            "correction": "Only verify it is visible, do not click",
        }

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _make_plan_payload(
                    [
                        {
                            "number": 1,
                            "action": "assert",
                            "element_name": "Get started",
                            "code": "await expect(getStarted).toBeVisible();",
                        },
                        {
                            "number": 2,
                            "action": "click",
                            "element_name": "Get started",
                            "code": "await getStarted.click();",
                        },
                    ],
                    "I will check that Get started is visible and click it",
                ),
            }
        )
    )

    note = loop._append_plan_correction_message(result["correction"])

    assert result["confirmed"] is False
    assert result["correction"] == "Only verify it is visible, do not click"
    assert result["phase"] == "planning"
    assert result["plan_id"].startswith("plan-")
    assert result["target_step_id"] == "step-1"
    assert loop.phase == "planning"
    assert loop.plan_confirmed is False
    assert loop.last_plan_ready_payload is None
    assert loop.last_plan_step_ids == []
    assert loop.last_plan_summary is None
    assert loop.last_plan_original_user_intent is None
    assert loop._active_plan_state is not None
    assert loop._active_plan_state["plan_id"] == result["plan_id"]
    assert loop._active_plan_correction_state is not None
    assert loop._active_plan_correction_state["plan_id"] == result["plan_id"]
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert len(sent_messages[0][1]["steps"][0]["children"]) == 2
    assert "Structured plan correction event." in note
    assert "active_plan_id:" in note
    assert "correction_type:" in note
    assert 'Correction: "Only verify it is visible, do not click"' in note
    assert 'Previous plan summary: "I will check that Get started is visible and click it"' in note
    assert "1. Check that Get started is visible and click it" in note
    assert "   expected_outcome: navigation · goes to docs intro page" in note
    assert "   - op_1 assert Get started is visible" in note
    assert "   - op_2 click Get started" in note
    assert "locator:" in note
    assert note == loop.llm.messages[-1]["content"]


def test_plan_confirmation_still_enters_execution_and_clears_context() -> None:
    loop = _make_loop()
    loop.current_steps = [_make_current_step()]
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
                "payload": _make_plan_payload(
                    [
                        {
                            "number": 1,
                            "action": "assert",
                            "element_name": "Get started",
                            "code": "await expect(getStarted).toBeVisible();",
                        }
                    ],
                    "I will check that Get started is visible",
                ),
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert loop.plan_confirmed is True
    assert loop.phase == "executing"
    assert loop.last_plan_ready_payload is None
    assert loop.last_plan_step_ids == []
    assert loop.last_plan_summary is None
    assert loop.last_plan_original_user_intent is None
    assert loop._current_active_plan_state() is None
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert len(sent_messages[0][1]["steps"][0]["children"]) >= 1
    assert sent_messages[0][1]["steps"][0]["children"][0]["type"] == "assert"


def test_plan_correction_triggers_replanned_plan_ready_before_execution(monkeypatch) -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    call_counter = {"count": 0}
    model_messages: list[list[dict[str, object]]] = []
    confirmation_calls = {"count": 0}

    loop.current_steps = [_make_current_step("Click the Get started button")]
    _install_common_run_stubs(loop, sent_messages)

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        confirmation_calls["count"] += 1
        if confirmation_calls["count"] == 1:
            return {
                "confirmed": False,
                "correction": "assert first then click",
            }
        loop.run_stop_requested = True
        return {"confirmed": True, "answer": "confirmed"}

    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    async def fake_model_call(*args, **kwargs):
        call_counter["count"] += 1
        messages = list(kwargs.get("messages") or [])
        model_messages.append(messages)
        if call_counter["count"] == 1:
            return _plan_ready_response(
                "call-1",
                [
                    {
                        "number": 1,
                        "action": "click",
                        "element_name": "Get started",
                        "code": "await getStarted.click();",
                    },
                ],
                "I will click Get started",
            )
        if call_counter["count"] == 2:
            user_messages = [message for message in messages if message.get("role") == "user"]
            assert user_messages
            correction_message = str(user_messages[-1].get("content") or "")
            assert "Structured plan correction event." in correction_message
            assert 'correction_type: "add_and_reorder_operations"' in correction_message
            assert 'Correction: "assert first then click"' in correction_message
            assert 'Previous plan summary: "I will click Get started"' in correction_message
            assert "   - op_1 click Get started" in correction_message
            diff_payload = {
                "target_step_id": "step-1",
                "mutations": [
                    {
                        "op": "add",
                        "position": "before",
                        "relative_to_operation_id": "op_1",
                        "operation": {
                            "type": "assert",
                            "target": "navigation",
                            "description": "navigation",
                            "assertion": "visible",
                        },
                    },
                    {
                        "op": "keep",
                        "operation_id": "op_1",
                    },
                ],
            }
            return _plan_correction_diff_response("call-2", diff_payload)
        if call_counter["count"] == 3:
            return _final_response("Done")
        return _final_response("Done")

    loop.model_router = SimpleNamespace(call=fake_model_call)
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step("Click the Get started button")]))

    assert call_counter["count"] == 3
    assert confirmation_calls["count"] == 2
    assert len(sent_messages) == 3
    assert sent_messages[0][0] == "plan_ready"
    assert len(sent_messages[0][1]["steps"][0]["children"]) == 1
    assert sent_messages[0][1]["steps"][0]["children"][0]["type"] == "click"
    assert sent_messages[1][0] == "plan_ready"
    assert len(sent_messages[1][1]["steps"][0]["children"]) == 2
    second_children = sent_messages[1][1]["steps"][0]["children"]
    assert [child["type"] for child in second_children] == ["assert", "click"]
    assert sent_messages[1][1]["steps"][0]["intent"] == "Click the Get started button"
    assert all(str(child.get("locator") or "").strip() for child in second_children)
    assert second_children[0]["operation_id"] == "op_2"
    assert second_children[1]["operation_id"] == "op_1"
    assert second_children[0]["locator"] == second_children[1]["locator"]
    assert sent_messages[2][0] == "llm_result"
    assert loop.run_stop_requested is False
    assert loop.plan_confirmed is False
    assert any("Structured plan correction event." in str(message.get("content") or "") for message in model_messages[1])
    assert all(message_type not in {"step_recorded", "code_update"} for message_type, _ in sent_messages)


def test_plan_correction_validation_preserves_reordered_children() -> None:
    loop = _make_loop()
    active_plan = _make_active_plan_state(
        "Click the Get started button and verify the page",
        [
            _make_operation("op_1", "click", "Get started"),
            _make_operation("op_2", "assert", "Get started is visible"),
        ],
        summary="I will click then verify Get started",
    )
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    proposed_payload = {
        "steps": [
            {
                "step_id": "step-1",
                "intent": "Assert that Get started is visible then click it",
                "children": [
                    _make_operation("temp-1", "assert", "Get started is visible"),
                    _make_operation("temp-2", "click", "Get started"),
                ],
            }
        ]
    }

    result = loop._validate_structured_plan_correction(proposed_payload)

    assert result["valid"] is True
    normalized_children = result["normalized_payload"]["steps"][0]["children"]
    assert [child["type"] for child in normalized_children] == ["assert", "click"]
    assert [child["operation_id"] for child in normalized_children] == ["op_2", "op_1"]


def test_plan_correction_diff_applies_assert_before_click_and_preserves_click_operation_id() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    active_plan["steps"][0]["expected_outcome"] = {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": {
                    "target_step_id": "step-1",
                    "mutations": [
                        {
                            "op": "add",
                            "position": "before",
                            "relative_to_operation_id": "op_1",
                            "operation": {
                                "type": "assert",
                                "target": "Get started",
                                "assertion": "visible",
                            },
                        },
                        {
                            "op": "keep",
                            "operation_id": "op_1",
                        },
                    ],
                },
            }
        )
    )

    children = sent_messages[0][1]["steps"][0]["children"]
    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert [child["type"] for child in children] == ["assert", "click"]
    assert [child["operation_id"] for child in children] == ["op_2", "op_1"]
    assert children[0]["assertion"] == "visible"
    assert children[0]["target"] == "Get started"
    assert children[0]["description"] == "Get started is visible"
    assert children[0]["target"] != "navigation"
    assert children[0]["description"] != "navigation"
    assert children[0]["locator"] == children[1]["locator"]
    assert children[1]["locator"] == 'get_by_label("Get started")'
    assert sent_messages[0][1]["steps"][0]["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    assert loop.plan_confirmed is True
    assert loop.phase == "executing"


@pytest.mark.parametrize("outcome_label", OUTCOME_LIKE_LABELS)
def test_plan_correction_added_assert_child_ignores_outcome_like_labels(outcome_label: str) -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the CTA button",
        [
            _make_operation(
                "op_1",
                "click",
                "CTA",
                target="CTA",
                locator='get_by_text("CTA", exact=True)',
            ),
        ],
        summary="I will click CTA",
    )
    active_plan["steps"][0]["expected_outcome"] = {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": {
                    "target_step_id": "step-1",
                    "mutations": [
                        {
                            "op": "add",
                            "position": "before",
                            "relative_to_operation_id": "op_1",
                            "operation": {
                                "type": "assert",
                                "target": outcome_label,
                                "description": outcome_label,
                                "assertion": "visible",
                            },
                        },
                        {
                            "op": "keep",
                            "operation_id": "op_1",
                        },
                    ],
                },
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    corrected_children = sent_messages[0][1]["steps"][0]["children"]
    assert [child["type"] for child in corrected_children] == ["assert", "click"]
    assert corrected_children[0]["target"] == "CTA"
    assert corrected_children[0]["description"] == "CTA is visible"
    assert corrected_children[0]["target"] != outcome_label
    assert corrected_children[0]["description"] != outcome_label
    assert corrected_children[0]["locator"] == 'get_by_text("CTA", exact=True)'
    assert corrected_children[1]["operation_id"] == "op_1"
    assert sent_messages[0][1]["steps"][0]["expected_outcome"]["type"] == "navigation"


def test_plan_correction_added_assert_child_preserves_valid_target_when_description_is_outcome_like() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Submit button",
        [
            _make_operation(
                "op_1",
                "click",
                "Submit",
                target="Submit",
                locator='get_by_text("Submit", exact=True)',
            ),
        ],
        summary="I will click Submit",
    )
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": {
                    "target_step_id": "step-1",
                    "mutations": [
                        {
                            "op": "add",
                            "position": "before",
                            "relative_to_operation_id": "op_1",
                            "operation": {
                                "type": "assert",
                                "target": "Header CTA",
                                "description": "navigation",
                                "assertion": "visible",
                            },
                        },
                        {
                            "op": "keep",
                            "operation_id": "op_1",
                        },
                    ],
                },
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_messages) == 1
    children = sent_messages[0][1]["steps"][0]["children"]
    assert [child["type"] for child in children] == ["assert", "click"]
    assert children[0]["target"] == "Header CTA"
    assert children[0]["description"] == "Header CTA is visible"
    assert children[0]["target"] != "navigation"
    assert children[0]["description"] != "navigation"
    assert children[0]["locator"] == 'get_by_text("Submit", exact=True)'


def test_plan_correction_added_assert_child_ignores_outcome_like_description_when_target_missing() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Submit button",
        [
            _make_operation(
                "op_1",
                "click",
                "Submit",
                target="Submit",
                locator='get_by_text("Submit", exact=True)',
            ),
        ],
        summary="I will click Submit",
    )
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": {
                    "target_step_id": "step-1",
                    "mutations": [
                        {
                            "op": "add",
                            "position": "before",
                            "relative_to_operation_id": "op_1",
                            "operation": {
                                "type": "assert",
                                "description": "modal",
                                "assertion": "visible",
                            },
                        },
                        {
                            "op": "keep",
                            "operation_id": "op_1",
                        },
                    ],
                },
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_messages) == 1
    children = sent_messages[0][1]["steps"][0]["children"]
    assert [child["type"] for child in children] == ["assert", "click"]
    assert children[0]["target"] == "Submit"
    assert children[0]["description"] == "Submit is visible"
    assert children[0]["description"] != "modal"
    assert children[0]["locator"] == 'get_by_text("Submit", exact=True)'


def test_plan_correction_added_assert_child_canonicalizes_has_text_description() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Check the page heading",
        [
            _make_operation(
                "op_1",
                "click",
                "Submit",
                target="Submit",
                locator='get_by_text("Submit", exact=True)',
            ),
        ],
        summary="I will click Submit",
    )
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": {
                    "target_step_id": "step-1",
                    "mutations": [
                        {
                            "op": "add",
                            "position": "before",
                            "relative_to_operation_id": "op_1",
                            "operation": {
                                "type": "assert",
                                "target": "Page heading",
                                "assertion": "has_text",
                                "value": "Welcome",
                            },
                        },
                        {
                            "op": "keep",
                            "operation_id": "op_1",
                        },
                    ],
                },
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_messages) == 1
    children = sent_messages[0][1]["steps"][0]["children"]
    assert [child["type"] for child in children] == ["assert", "click"]
    assert children[0]["target"] == "Page heading"
    assert children[0]["assertion"] == "has_text"
    assert children[0]["value"] == "Welcome"
    assert children[0]["description"] == "Page heading has text Welcome"
    assert children[0]["locator"] == 'get_by_text("Submit", exact=True)'


def test_plan_correction_diff_allows_explicit_removal() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Check that Get started is visible and click it",
        [
            _make_operation("op_1", "assert", "Get started is visible"),
            _make_operation("op_2", "click", "Get started"),
        ],
        summary="I will check and click Get started",
    )
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "only assert, don't click",
        source_plan_state=active_plan,
    )

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": {
                    "target_step_id": "step-1",
                    "mutations": [
                        {
                            "op": "keep",
                            "operation_id": "op_1",
                        },
                        {
                            "op": "remove",
                            "operation_id": "op_2",
                        },
                    ],
                },
            }
        )
    )

    children = sent_messages[0][1]["steps"][0]["children"]
    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert [child["type"] for child in children] == ["assert"]
    assert [child["operation_id"] for child in children] == ["op_1"]
    assert loop.plan_confirmed is True
    assert loop.phase == "executing"


def test_plan_correction_diff_reorders_without_dropping_children() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Check that Get started is visible and click it",
        [
            _make_operation("op_1", "click", "Get started"),
            _make_operation("op_2", "assert", "Get started is visible"),
        ],
        summary="I will click then verify Get started",
    )
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": {
                    "target_step_id": "step-1",
                    "mutations": [
                        {
                            "op": "reorder",
                            "operation_id": "op_2",
                        },
                        {
                            "op": "keep",
                            "operation_id": "op_1",
                        },
                    ],
                },
            }
        )
    )

    children = sent_messages[0][1]["steps"][0]["children"]
    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert [child["type"] for child in children] == ["assert", "click"]
    assert [child["operation_id"] for child in children] == ["op_2", "op_1"]
    assert loop.plan_confirmed is True
    assert loop.phase == "executing"


def test_plan_correction_retry_budget_blocks_silent_drop_then_requires_clarification() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop.current_steps = [_make_current_step("Click the Get started button")]
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    loop._plan_correction_pending = True

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    invalid_payload = {
        "message_type": "plan_correction_diff",
        "payload": {
            "target_step_id": "step-1",
            "mutations": [
                {
                    "op": "add",
                    "position": "before",
                    "relative_to_operation_id": "op_1",
                    "operation": {
                        "type": "assert",
                        "target": "Get started",
                        "assertion": "visible",
                    },
                },
            ],
        },
    }

    first_result = asyncio.run(loop._tool_send_to_overlay(invalid_payload))
    assert first_result["blocked"] is True
    assert first_result["reason"] == "invalid_corrected_plan"
    assert first_result["message"] == (
        "Corrected plan is invalid because existing click operation was dropped. "
        "Return one parent step with assert then click."
    )
    assert sent_messages == []
    assert loop.llm.messages == []
    assert loop._active_plan_correction_state is not None
    assert loop._active_plan_correction_state["retry_count"] == 1
    assert loop._active_plan_correction_state["needs_clarification"] is False

    second_result = asyncio.run(loop._tool_send_to_overlay(invalid_payload))
    assert second_result["blocked"] is True
    assert second_result["reason"] == "invalid_corrected_plan"
    assert second_result["message"] == "Should I keep the click and add an assertion before it?"
    assert sent_messages == []
    assert loop.llm.messages == []
    assert loop._active_plan_correction_state is not None
    assert loop._active_plan_correction_state["retry_count"] == 2
    assert loop._active_plan_correction_state["needs_clarification"] is True
    assert loop._active_plan_correction_state["clarification_question"] == second_result["message"]
    assert loop._active_plan_correction_state["clarification_answer"] is None
    assert loop._active_plan_correction_state["clarification_resolved"] is False
    assert loop._active_plan_correction_state["clarification_closed"] is False


def test_plan_correction_llm_thinking_schema_retry_then_fails_closed() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    correction_state["clarification_resolved"] = True
    correction_state["needs_clarification"] = False
    loop._active_plan_correction_state = correction_state

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "llm_thinking",
                "payload": {"note": "thinking"},
            }
        )
    )

    assert result["blocked"] is True
    assert result["reason"] == "correction_schema_retry"
    assert "plan_correction_diff" in str(result.get("message") or "")
    assert sent_messages == []
    assert loop._active_plan_correction_state is not None
    assert not loop._active_plan_correction_state.get("correction_failed")
    assert loop._active_plan_correction_state["schema_retry_count"] == 1
    assert loop._active_plan_correction_state["no_progress_count"] == 1

    second_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "llm_thinking",
                "payload": {"note": "thinking again"},
            }
        )
    )

    assert second_result["blocked"] is True
    assert second_result["reason"] == "correction_failed"
    assert loop._active_plan_correction_state["correction_failed"] is True
    assert loop._active_plan_correction_state["clarification_closed"] is True
    assert loop._active_plan_correction_state["no_progress_count"] == 2
    assert loop._active_plan_correction_state["schema_retry_count"] == 2


def test_plan_correction_validation_allows_explicit_removal() -> None:
    loop = _make_loop()
    active_plan = _make_active_plan_state(
        "Check that Get started is visible and click it",
        [
            _make_operation("op_1", "assert", "Get started is visible"),
            _make_operation("op_2", "click", "Get started"),
        ],
        summary="I will check and click Get started",
    )
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "only assert, don't click",
        source_plan_state=active_plan,
    )

    proposed_payload = {
        "steps": [
            {
                "step_id": "step-1",
                "intent": "Check that Get started is visible",
                "children": [
                    _make_operation("temp-1", "assert", "Get started is visible"),
                ],
            }
        ]
    }

    result = loop._validate_structured_plan_correction(proposed_payload)

    assert result["valid"] is True
    normalized_children = result["normalized_payload"]["steps"][0]["children"]
    assert [child["type"] for child in normalized_children] == ["assert"]
    assert [child["operation_id"] for child in normalized_children] == ["op_1"]


def test_plan_correction_ambiguous_correction_filters_tools_to_ask_user() -> None:
    loop = _make_loop()
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "make it proper",
        source_plan_state=active_plan,
    )
    loop._active_plan_correction_state = correction_state

    tools = [
        {"type": "function", "function": {"name": "send_to_overlay"}},
        {"type": "function", "function": {"name": "locator_find"}},
        {"type": "function", "function": {"name": "locator_validate"}},
        {"type": "function", "function": {"name": "ask_user"}},
        {"type": "function", "function": {"name": "browser_get_state"}},
    ]

    filtered_tools = filter_tools_for_phase(tools, "planning", correction_mode=correction_state)

    assert correction_state["category"] == "ambiguous"
    assert [tool["function"]["name"] for tool in filtered_tools] == ["ask_user"]


@pytest.mark.parametrize("answer", ["yes", "no"])
def test_plan_correction_clarification_answer_reopens_plan_ready_and_updates_state(answer: str) -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send
    correction_state = _make_waiting_correction_state(loop)
    loop.control_queue = _QueuedEvents([{"type": "option_selected", "answer": answer}])

    result = asyncio.run(
        loop._tool_ask_user(
            {"question": str(correction_state["clarification_question"] or "")}
        )
    )

    tools = [
        {"type": "function", "function": {"name": "send_to_overlay"}},
        {"type": "function", "function": {"name": "locator_find"}},
        {"type": "function", "function": {"name": "locator_validate"}},
        {"type": "function", "function": {"name": "ask_user"}},
        {"type": "function", "function": {"name": "browser_get_state"}},
    ]
    filtered_tools = filter_tools_for_phase(tools, "planning", correction_mode=loop._active_plan_correction_state)

    assert result["success"] is True
    assert result["event_type"] == "option_selected"
    assert result["answer"] == answer
    assert result["clarification_resolved"] is True
    assert result["clarification_answer"] == answer
    assert "Structured correction clarification resolved." in str(result["clarification_resolution_message"] or "")
    assert f'User answered: "{answer}"' in str(result["clarification_resolution_message"] or "")
    assert loop._active_plan_correction_state is not None
    assert loop._active_plan_correction_state["needs_clarification"] is False
    assert loop._active_plan_correction_state["clarification_resolved"] is True
    assert loop._active_plan_correction_state["clarification_answer"] == answer
    assert loop._active_plan_correction_state["clarification_closed"] is False
    assert loop._active_plan_correction_state["clarification_question"] == "Should I keep the click and add an assertion before it?"
    assert [tool["function"]["name"] for tool in filtered_tools] == ["send_to_overlay"]
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "clarification_needed"


def test_plan_correction_duplicate_clarification_is_blocked_after_answer() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send
    correction_state = _make_waiting_correction_state(loop)
    loop.control_queue = _QueuedEvents([{"type": "option_selected", "answer": "yes"}])

    first_result = asyncio.run(
        loop._tool_ask_user({"question": str(correction_state["clarification_question"] or "")})
    )
    assert first_result["clarification_resolved"] is True

    loop.control_queue = _QueuedEvents([])
    duplicate_result = asyncio.run(
        loop._tool_ask_user({"question": str(correction_state["clarification_question"] or "")})
    )

    assert duplicate_result["blocked"] is True
    assert duplicate_result["skipped"] is True
    assert duplicate_result["reason"] == "clarification_already_answered"
    assert duplicate_result["message"] == "Clarification already answered. Produce a correction diff."
    assert duplicate_result["clarification_resolved"] is True
    assert duplicate_result["requires_replan"] is False
    assert loop._active_plan_correction_state is not None
    assert loop._active_plan_correction_state["correction_failed"] is True
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "clarification_needed"


def test_plan_correction_post_clarification_invalid_plan_closes_flow() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send
    correction_state = _make_waiting_correction_state(loop)
    loop.control_queue = _QueuedEvents([{"type": "option_selected", "answer": "yes"}])

    answer_result = asyncio.run(
        loop._tool_ask_user({"question": str(correction_state["clarification_question"] or "")})
    )
    assert answer_result["clarification_resolved"] is True

    invalid_payload = {
        "message_type": "plan_correction_diff",
        "payload": {
            "target_step_id": "step-1",
            "mutations": [
                {
                    "op": "add",
                    "position": "before",
                    "relative_to_operation_id": "op_1",
                    "operation": {
                        "type": "assert",
                        "target": "Get started",
                        "assertion": "visible",
                    },
                },
            ],
        },
    }

    failure_result = asyncio.run(loop._tool_send_to_overlay(invalid_payload))

    loop.control_queue = _QueuedEvents([])
    blocked_result = asyncio.run(
        loop._tool_ask_user({"question": str(correction_state["clarification_question"] or "")})
    )

    assert failure_result["blocked"] is True
    assert failure_result["reason"] == "correction_failed"
    assert "Corrected plan is still invalid after clarification." in str(failure_result["message"] or "")
    assert loop._active_plan_correction_state is not None
    assert loop._active_plan_correction_state["clarification_closed"] is True
    assert loop._active_plan_correction_state["needs_clarification"] is False
    assert loop._active_plan_correction_state["correction_failed"] is True
    assert blocked_result["blocked"] is True
    assert blocked_result["reason"] == "clarification_already_answered"
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "clarification_needed"


def test_plan_correction_clarification_answer_allows_final_corrected_plan_ready(monkeypatch) -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    call_counter = {"count": 0}
    model_messages: list[list[dict[str, object]]] = []
    confirmation_calls = {"count": 0}

    loop.current_steps = [_make_current_step("Click the Get started button")]
    _install_common_run_stubs(loop, sent_messages)
    loop.control_queue = _QueuedEvents([{"type": "option_selected", "answer": "yes"}])

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        confirmation_calls["count"] += 1
        if confirmation_calls["count"] == 1:
            return {
                "confirmed": False,
                "correction": "assert first then click",
            }
        loop.run_stop_requested = True
        return {"confirmed": True, "answer": "confirmed"}

    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    async def fake_model_call(*args, **kwargs):
        call_counter["count"] += 1
        messages = list(kwargs.get("messages") or [])
        model_messages.append(messages)
        if call_counter["count"] == 1:
            return _plan_ready_response(
                "call-1",
                [
                    {
                        "number": 1,
                        "action": "click",
                        "element_name": "Get started",
                        "code": "await getStarted.click();",
                    },
                ],
                "I will click Get started",
            )
        if call_counter["count"] == 2:
            user_messages = [message for message in messages if message.get("role") == "user"]
            assert user_messages
            correction_message = str(user_messages[-1].get("content") or "")
            assert "Structured plan correction event." in correction_message
            assert 'Correction: "assert first then click"' in correction_message
            diff_payload = {
                "target_step_id": "step-1",
                "mutations": [
                    {
                        "op": "add",
                        "position": "before",
                        "relative_to_operation_id": "op_1",
                        "operation": {
                            "type": "assert",
                            "target": "Get started",
                            "assertion": "visible",
                        },
                    },
                    {
                        "op": "keep",
                        "operation_id": "op_1",
                    },
                ],
            }
            return _plan_correction_diff_response("call-2", diff_payload)
        return _final_response("Done")

    loop.model_router = SimpleNamespace(call=fake_model_call)
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step("Click the Get started button")]))

    message_types = [message_type for message_type, _ in sent_messages]
    assert call_counter["count"] == 3
    assert confirmation_calls["count"] == 2
    assert message_types == ["plan_ready", "plan_ready", "llm_result"]
    assert loop.run_stop_requested is False
    assert loop.plan_confirmed is False
    assert len(sent_messages[0][1]["steps"][0]["children"]) == 1
    assert len(sent_messages[1][1]["steps"][0]["children"]) == 2
    assert [child["type"] for child in sent_messages[1][1]["steps"][0]["children"]] == ["assert", "click"]
    assert [child["operation_id"] for child in sent_messages[1][1]["steps"][0]["children"]] == ["op_2", "op_1"]
    assert any("Structured plan correction event." in str(message.get("content") or "") for message in model_messages[1])


def test_plan_correction_plan_ready_schema_retry() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    loop._active_plan_correction_state = correction_state

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _make_plan_payload(
                    [
                        {
                            "number": 1,
                            "action": "click",
                            "element_name": "Get started",
                            "code": "await getStarted.click();",
                        },
                    ],
                    "I will click Get started",
                ),
            }
        )
    )

    assert result["blocked"] is True
    assert result["reason"] == "correction_schema_retry"
    assert "plan_correction_diff" in str(result.get("message") or "")
    assert loop._active_plan_correction_state is not None
    assert not loop._active_plan_correction_state.get("correction_failed")
    assert loop._active_plan_correction_state["schema_retry_count"] == 1
    assert loop._active_plan_correction_state["no_progress_count"] == 1


def test_plan_correction_plan_ready_twice_fails_closed() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    loop._active_plan_correction_state = correction_state

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    first_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _make_plan_payload(
                    [
                        {
                            "number": 1,
                            "action": "click",
                            "element_name": "Get started",
                            "code": "await getStarted.click();",
                        },
                    ],
                    "I will click Get started",
                ),
            }
        )
    )

    assert first_result["blocked"] is True
    assert first_result["reason"] == "correction_schema_retry"
    assert loop._active_plan_correction_state["schema_retry_count"] == 1

    second_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_ready",
                "payload": _make_plan_payload(
                    [
                        {
                            "number": 1,
                            "action": "click",
                            "element_name": "Get started",
                            "code": "await getStarted.click();",
                        },
                    ],
                    "I will click Get started",
                ),
            }
        )
    )

    assert second_result["blocked"] is True
    assert second_result["reason"] == "correction_diff_required"
    assert loop._active_plan_correction_state["correction_failed"] is True
    assert loop._active_plan_correction_state["clarification_closed"] is True
    assert loop._active_plan_correction_state["schema_retry_count"] == 2


def test_plan_correction_valid_diff_after_schema_retry_succeeds() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    loop._active_plan_correction_state = correction_state

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {"confirmed": True, "answer": "confirmed"}

    loop._send = fake_send
    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    first_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "llm_thinking",
                "payload": {"note": "thinking"},
            }
        )
    )

    assert first_result["blocked"] is True
    assert first_result["reason"] == "correction_schema_retry"
    assert loop._active_plan_correction_state["schema_retry_count"] == 1
    assert not loop._active_plan_correction_state.get("correction_failed")

    second_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": {
                    "target_step_id": "step-1",
                    "mutations": [
                        {
                            "op": "add",
                            "position": "before",
                            "relative_to_operation_id": "op_1",
                            "operation": {
                                "type": "assert",
                                "target": "Get started",
                                "assertion": "visible",
                            },
                        },
                        {
                            "op": "keep",
                            "operation_id": "op_1",
                        },
                    ],
                },
            }
        )
    )

    assert second_result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    children = sent_messages[0][1]["steps"][0]["children"]
    assert [child["type"] for child in children] == ["assert", "click"]
    assert [child["operation_id"] for child in children] == ["op_2", "op_1"]
    assert all(str(child.get("locator") or "").strip() for child in children)
    assert loop.plan_confirmed is True
    assert loop.confirmed_plan_step_ids == ["step-1"]
    confirmed_plan = loop.confirmed_plan_by_step_id["step-1"]
    assert confirmed_plan["step_id"] == "step-1"
    assert confirmed_plan["step_number"] == 1
    assert confirmed_plan["parent_intent"] == "Click the Get started button"
    assert [child["type"] for child in confirmed_plan["children"]] == ["assert", "click"]
    assert [child["operation_id"] for child in confirmed_plan["children"]] == ["op_2", "op_1"]

    stored_confirmed_plan = loop.confirmed_plan_by_step_id["step-1"]
    loop._clear_active_plan_state()
    assert loop._current_active_plan_state() is None
    assert loop.confirmed_plan_by_step_id["step-1"] == stored_confirmed_plan


def test_plan_correction_schema_retry_context_message_is_explicit() -> None:
    loop = _make_loop()
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    loop._active_plan_correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    context_message = loop._build_plan_correction_context_message()

    assert "You MUST respond with send_to_overlay message_type='plan_correction_diff'" in context_message
    assert "Do NOT respond with plan_ready" in context_message
    assert "Do NOT respond with llm_thinking" in context_message
    assert "Do NOT use ask_user unless" in context_message


def test_plan_correction_schema_retry_count_initializes_to_zero() -> None:
    loop = _make_loop()
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )

    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )

    assert correction_state["schema_retry_count"] == 0
    assert correction_state["no_progress_count"] == 0


def test_plan_correction_correction_failed_preserves_active_plan_state() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    loop._active_plan_correction_state = correction_state

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    loop._active_plan_correction_state["schema_retry_count"] = 2
    loop._active_plan_correction_state["correction_failed"] = True
    loop._active_plan_correction_state["clarification_closed"] = True
    loop._active_plan_correction_state["no_progress_count"] = 2

    failure_message = "Correction failed safely. You can edit the pending step or run it again."
    loop._active_plan_correction_state["last_validation_feedback"] = failure_message

    original_plan_id = active_plan["plan_id"]
    original_step_id = active_plan["target_step_id"]

    loop._clear_active_plan_correction_state()

    assert loop._active_plan_correction_state is None
    assert loop._plan_correction_pending is False
    assert loop._active_plan_state is not None
    assert loop._active_plan_state["plan_id"] == original_plan_id
    assert loop._active_plan_state["target_step_id"] == original_step_id


def test_plan_correction_no_tool_calls_schema_retry(monkeypatch) -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    call_counter = {"count": 0}
    confirmation_counter = {"count": 0}

    loop.current_steps = [_make_current_step("Click the Get started button")]
    _install_common_run_stubs(loop, sent_messages)

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        confirmation_counter["count"] += 1
        if confirmation_counter["count"] == 1:
            return {
                "confirmed": False,
                "correction": "assert first then click",
            }
        loop.run_stop_requested = True
        return {"confirmed": True, "answer": "confirmed"}

    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    async def fake_model_call(*args, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            return _plan_ready_response(
                "call-1",
                [
                    {
                        "number": 1,
                        "action": "click",
                        "element_name": "Get started",
                        "code": "await getStarted.click();",
                    },
                ],
                "I will click Get started",
            )
        if call_counter["count"] == 2:
            return _final_response("Let me think about this correction.")
        if call_counter["count"] == 3:
            diff_payload = {
                "target_step_id": "step-1",
                "mutations": [
                    {
                        "op": "add",
                        "position": "before",
                        "relative_to_operation_id": "op_1",
                        "operation": {
                            "type": "assert",
                            "target": "Get started",
                            "assertion": "visible",
                        },
                    },
                    {
                        "op": "keep",
                        "operation_id": "op_1",
                    },
                ],
            }
            return _plan_correction_diff_response("call-3", diff_payload)
        loop.run_stop_requested = True
        return _final_response("Done")

    loop.model_router = SimpleNamespace(call=fake_model_call)
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step("Click the Get started button")]))

    assert call_counter["count"] >= 2
    retry_messages = [
        msg for msg in loop.llm.messages
        if msg.get("role") == "user"
        and "plan_correction_diff" in str(msg.get("content") or "")
        and "Do not send plan_ready" in str(msg.get("content") or "")
    ]
    assert len(retry_messages) >= 1


def test_plan_correction_no_tool_calls_twice_fails_closed(monkeypatch) -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    call_counter = {"count": 0}

    loop.current_steps = [_make_current_step("Click the Get started button")]
    _install_common_run_stubs(loop, sent_messages)

    async def fake_wait_for_plan_confirmation() -> dict[str, object]:
        return {
            "confirmed": False,
            "correction": "assert first then click",
        }

    loop._wait_for_plan_confirmation = fake_wait_for_plan_confirmation

    async def fake_model_call(*args, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            return _plan_ready_response(
                "call-1",
                [
                    {
                        "number": 1,
                        "action": "click",
                        "element_name": "Get started",
                        "code": "await getStarted.click();",
                    },
                ],
                "I will click Get started",
            )
        if call_counter["count"] >= 2:
            return _final_response("I am thinking about this.")

    loop.model_router = SimpleNamespace(call=fake_model_call)
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step("Click the Get started button")]))

    assert call_counter["count"] == 3
    llm_result_messages = [
        (msg_type, kwargs) for msg_type, kwargs in sent_messages
        if msg_type == "llm_result"
    ]
    assert len(llm_result_messages) >= 1
    assert any("Correction failed" in str(kwargs.get("message") or "") for _, kwargs in llm_result_messages)
    assert loop._active_plan_correction_state is None


def test_plan_correction_tool_call_sequencing_on_schema_retry() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    loop._active_plan_correction_state = correction_state

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    result = asyncio.run(loop._tool_send_to_overlay(
        {"message_type": "llm_thinking", "payload": {"note": "thinking"}}
    ))

    assert result["blocked"] is True
    assert result["reason"] == "correction_schema_retry"
    assert isinstance(result.get("message"), str)
    assert "plan_correction_diff" in result["message"]


def test_plan_correction_normal_plan_ready_outside_correction_still_works() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    loop.current_steps = [_make_current_step("Click the Get started button")]

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
                "payload": _make_plan_payload(
                    [
                        {
                            "number": 1,
                            "action": "click",
                            "element_name": "Get started",
                            "code": "await getStarted.click();",
                        },
                    ],
                    "I will click Get started",
                ),
            }
        )
    )

    assert result == {"confirmed": True, "answer": "confirmed", "phase": "executing"}
    assert loop.plan_confirmed is True
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "plan_ready"
    assert loop._active_plan_correction_state is None


def test_plan_correction_invalid_diff_after_schema_retry_fails_closed() -> None:
    loop = _make_loop()
    sent_messages: list[tuple[str, dict[str, object]]] = []
    active_plan = _make_active_plan_state(
        "Click the Get started button",
        [_make_operation("op_1", "click", "Get started")],
        summary="I will click Get started",
    )
    loop._active_plan_state = active_plan
    correction_state = loop._build_plan_correction_state(
        "assert first then click",
        source_plan_state=active_plan,
    )
    loop._active_plan_correction_state = correction_state

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_messages.append((message_type, kwargs))

    loop._send = fake_send

    first_result = asyncio.run(
        loop._tool_send_to_overlay(
            {
                "message_type": "llm_thinking",
                "payload": {"note": "thinking"},
            }
        )
    )

    assert first_result["reason"] == "correction_schema_retry"
    assert not loop._active_plan_correction_state.get("correction_failed")

    invalid_payload = {
        "message_type": "plan_correction_diff",
        "payload": {
            "target_step_id": "step-1",
            "mutations": [
                {
                    "op": "add",
                    "position": "before",
                    "relative_to_operation_id": "op_1",
                    "operation": {
                        "type": "assert",
                        "target": "Get started",
                        "assertion": "visible",
                    },
                },
            ],
        },
    }

    second_result = asyncio.run(loop._tool_send_to_overlay(invalid_payload))

    assert second_result["blocked"] is True
    assert second_result["reason"] == "invalid_corrected_plan"
    assert loop._active_plan_correction_state["retry_count"] == 1
    assert not loop._active_plan_correction_state.get("correction_failed")
