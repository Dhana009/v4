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
    loop.confirmed_plan_by_step_id = {}
    loop.confirmed_plan_step_ids = []
    loop.confirmed_child_results_by_step_id = {}
    loop.confirmed_execution_mismatch_count_by_step_id = {}
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


def _make_planned_child(
    operation_id: str,
    child_type: str,
    description: str,
    target: str = "Get started",
    locator: str = 'get_by_label("Get started")',
    assertion: str | None = None,
) -> dict[str, object]:
    child = {
        "operation_id": operation_id,
        "type": child_type,
        "description": description,
        "target": target,
        "locator": locator,
        "status": "planned",
    }
    if assertion is not None:
        child["assertion"] = assertion
    return child


def _make_confirmed_plan_payload(
    step_context: dict[str, object],
    children: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "plan_id": "plan-1",
        "summary": "I will check and click Get started",
        "original_user_intent": str(step_context.get("intent") or ""),
        "steps": [
            {
                "step_id": step_context["step_id"],
                "step_number": step_context["step_number"],
                "intent": step_context["intent"],
                "expected_outcome": step_context["expected_outcome"],
                "children": children,
            }
        ],
    }


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
    assert len(sent_messages) == 3
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[1][0] == "code_update"
    assert sent_messages[2][0] == "run_completed"

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
    run_completed_payload = sent_messages[2][1]
    assert run_completed_payload["recorded_count"] == 1
    assert run_completed_payload["skipped_count"] == 0
    assert run_completed_payload["summary"]


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
    assert len(sent_messages) == 3
    payload = sent_messages[0][1]
    assert payload["step_id"] == "pending-step-mooeb8ca-2"
    assert payload["expected_outcome"] == {
        "type": "navigation",
        "description": "thus assertion on the new page after clicking the button",
        "source": "user",
        "required": True,
    }
    assert sent_messages[1][0] == "code_update"
    assert sent_messages[2][0] == "run_completed"


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


def test_step_recorded_payload_prefers_confirmed_execution_template_when_available() -> None:
    loop = _make_loop()
    step_context = _make_step_context(
        expected_outcome={
            "type": "navigation",
            "description": "goes to docs intro page",
            "source": "user",
            "required": True,
        }
    )
    step_context["intent"] = "Check that Get started is visible and click it"
    step_context["element_info"] = {
        "text": "Get started",
        "attributes": {"aria-label": "Get started"},
    }
    step_context["element_name"] = "Get started"
    assert_result = _make_assert_success_record(step_context)
    click_result = _make_action_record(
        step_context,
        "action_click",
        "click",
        'get_by_label("Get started")',
    )
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "step-1"
    loop.plan_confirmed = True
    loop._active_plan_state = {
        "plan_id": "plan-1",
        "summary": "I will check and click Get started",
        "original_user_intent": step_context["intent"],
        "steps": [step_context],
    }
    loop._store_confirmed_execution_plan(
        _make_confirmed_plan_payload(
            step_context,
            [
                _make_planned_child("op_1", "assert", "Get started is visible", assertion="visible"),
                _make_planned_child("op_2", "click", "Get started"),
            ],
        )
    )
    loop.confirmed_child_results_by_step_id["step-1"] = {
        "op_1": {**assert_result, "status": "success"},
        "op_2": {**click_result, "status": "success"},
    }
    loop.last_successful_action = click_result
    loop.successful_action_by_step_id = {"step-1": click_result}
    loop.successful_actions_by_step_id = {"step-1": [assert_result, click_result]}

    payload = loop._build_step_record_payload(
        {
            "step_id": "step-1",
            "step_number": 1,
        },
        step_context,
    )
    code_update_payload = loop._build_code_update_payload(payload, "step-1")
    children = payload["children"]
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

    assert payload["step_id"] == "step-1"
    assert payload["action"] == "click"
    assert payload["locator"] == 'get_by_label("Get started")'
    assert payload["status"] == "success"
    assert isinstance(children, list)
    assert [child["operation_id"] for child in children] == ["op_1", "op_2"]
    assert [child["type"] for child in children] == ["assert", "click"]
    assert [child["status"] for child in children] == ["success", "success"]
    assert children[0]["assertion"] == "visible"
    assert children[0]["code_lines"] == [assert_line]
    assert children[1]["code_lines"] == [click_line]
    assert code_update_payload["lines"] == [assert_line, click_line]
    assert code_update_payload["full_spec_preview"] == "\n".join([assert_line, click_line])


def test_step_recorded_payload_refuses_click_only_recording_when_confirmed_assert_is_not_complete() -> None:
    loop = _make_loop()
    step_context = _make_step_context(
        expected_outcome={
            "type": "navigation",
            "description": "goes to docs intro page",
            "source": "user",
            "required": True,
        }
    )
    step_context["intent"] = "Check that Get started is visible and click it"
    step_context["element_info"] = {
        "text": "Get started",
        "attributes": {"aria-label": "Get started"},
    }
    step_context["element_name"] = "Get started"
    click_result = _make_action_record(
        step_context,
        "action_click",
        "click",
        'get_by_label("Get started")',
    )
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "step-1"
    loop.plan_confirmed = True
    loop._active_plan_state = {
        "plan_id": "plan-1",
        "summary": "I will check and click Get started",
        "original_user_intent": step_context["intent"],
        "steps": [step_context],
    }
    loop._store_confirmed_execution_plan(
        _make_confirmed_plan_payload(
            step_context,
            [
                _make_planned_child("op_1", "assert", "Get started is visible", assertion="visible"),
                _make_planned_child("op_2", "click", "Get started"),
            ],
        )
    )
    loop.confirmed_child_results_by_step_id["step-1"] = {
        "op_1": {
            "operation_id": "op_1",
            "step_id": "step-1",
            "step_number": 1,
            "type": "assert",
            "target": "Get started",
            "locator": 'get_by_label("Get started")',
            "assertion": "visible",
            "status": "blocked",
            "tool": "action_assert",
            "action": "assert",
            "action_context": {
                "locator": 'page.title',
                "assertion": "has_text",
                "expected_value": "Fast and reliable...",
            },
            "tool_args": {
                "locator": 'page.title',
                "assertion": "has_text",
                "expected_value": "Fast and reliable...",
            },
            "result": {
                "success": False,
                "blocked": True,
                "reason": "execution_contract_mismatch",
                "message": "Execution blocked: confirmed plan expected assert visible on Get started, but model tried page.title has_text.",
            },
            "attempts": [],
        },
        "op_2": {**click_result, "status": "success"},
    }
    loop.last_successful_action = click_result
    loop.successful_action_by_step_id = {"step-1": click_result}
    loop.successful_actions_by_step_id = {"step-1": [click_result]}

    payload = loop._build_step_record_payload(
        {
            "step_id": "step-1",
            "step_number": 1,
        },
        step_context,
    )

    assert payload == {}


def test_confirmed_execution_contract_accepts_exact_text_alias_with_has_text_actual() -> None:
    loop = _make_loop()
    exact_text = "npx playwright init-agents --loop=opencode"
    exact_locator = f'get_by_text("{exact_text}", exact=True)'
    step_context = _make_step_context(
        expected_outcome={
            "type": "no_visible_change",
            "description": "stays on the current page",
            "source": "user",
            "required": False,
        }
    )
    step_context["intent"] = f"Assert exact text equal to {exact_text}"
    step_context["element_name"] = exact_text
    step_context["element_info"] = {
        "text": f"VS Code Claude Code OpenCode {exact_text}",
        "attributes": {"aria-label": exact_text},
    }
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop.confirmed_plan_by_step_id = {
        "step-1": {
            "step_id": "step-1",
            "step_number": 1,
            "parent_intent": step_context["intent"],
            "expected_outcome": step_context["expected_outcome"],
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert",
                    "target": exact_text,
                    "locator": exact_locator,
                    "assertion": "exact_text",
                    "value": exact_text,
                    "expected_value": exact_text,
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": "Assert command text",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}

    allowed_result = loop._validate_confirmed_execution_tool_call(
        "action_assert",
        {
            "locator": exact_locator,
            "assertion": "has_text",
            "expected_value": exact_text,
        },
    )

    assert allowed_result["allowed"] is True
    assert allowed_result["step_id"] == "step-1"
    assert allowed_result["expected_child"]["assertion"] == "exact_text"


def test_confirmed_execution_contract_accepts_single_quoted_locator_equivalent() -> None:
    loop = _make_loop()
    element_name = "Playwright Test Agents"
    expected_locator = f'get_by_role("heading", name="{element_name}")'
    actual_locator = f"get_by_role('heading', name='{element_name}')"
    step_context = _make_step_context()
    step_context["intent"] = f"Assert {element_name} is visible"
    step_context["element_name"] = element_name
    step_context["element_info"] = {
        "text": element_name,
        "attributes": {"aria-label": element_name},
    }
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop.confirmed_plan_by_step_id = {
        "step-1": {
            "step_id": "step-1",
            "step_number": 1,
            "parent_intent": step_context["intent"],
            "expected_outcome": step_context["expected_outcome"],
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert",
                    "target": element_name,
                    "locator": expected_locator,
                    "assertion": "visible",
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": f"Assert {element_name} is visible",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}

    allowed_result = loop._validate_confirmed_execution_tool_call(
        "action_assert",
        {
            "locator": actual_locator,
            "assertion": "visible",
        },
    )

    assert allowed_result["allowed"] is True
    assert allowed_result["expected_child"]["locator"] == expected_locator


def test_confirmed_execution_contract_accepts_double_quoted_locator_equivalent_in_reverse() -> None:
    loop = _make_loop()
    element_name = "Playwright Test Agents"
    expected_locator = f"get_by_role('heading', name='{element_name}')"
    actual_locator = f'get_by_role("heading", name="{element_name}")'
    step_context = _make_step_context()
    step_context["intent"] = f"Assert {element_name} is visible"
    step_context["element_name"] = element_name
    step_context["element_info"] = {
        "text": element_name,
        "attributes": {"aria-label": element_name},
    }
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop.confirmed_plan_by_step_id = {
        "step-1": {
            "step_id": "step-1",
            "step_number": 1,
            "parent_intent": step_context["intent"],
            "expected_outcome": step_context["expected_outcome"],
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert",
                    "target": element_name,
                    "locator": expected_locator,
                    "assertion": "visible",
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": f"Assert {element_name} is visible",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}

    allowed_result = loop._validate_confirmed_execution_tool_call(
        "action_assert",
        {
            "locator": actual_locator,
            "assertion": "visible",
        },
    )

    assert allowed_result["allowed"] is True
    assert allowed_result["expected_child"]["locator"] == expected_locator


def test_confirmed_execution_contract_rejects_different_locator_text() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    step_context["intent"] = "Assert Submit is visible"
    step_context["element_name"] = "Submit"
    step_context["element_info"] = {
        "text": "Submit",
        "attributes": {"aria-label": "Submit"},
    }
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop.confirmed_plan_by_step_id = {
        "step-1": {
            "step_id": "step-1",
            "step_number": 1,
            "parent_intent": step_context["intent"],
            "expected_outcome": step_context["expected_outcome"],
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert",
                    "target": "Submit",
                    "locator": 'get_by_label("Submit")',
                    "assertion": "visible",
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": "Assert Submit is visible",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}

    blocked_result = loop._validate_confirmed_execution_tool_call(
        "action_assert",
        {
            "locator": 'get_by_label("Cancel")',
            "assertion": "visible",
        },
    )

    assert blocked_result["blocked"] is True
    assert blocked_result["reason"] == "execution_contract_mismatch"
    assert blocked_result["expected_child"]["locator"] == 'get_by_label("Submit")'


def test_confirmed_execution_contract_rejects_different_locator_strategy_with_same_text() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    step_context["intent"] = "Assert Submit is visible"
    step_context["element_name"] = "Submit"
    step_context["element_info"] = {
        "text": "Submit",
        "attributes": {"aria-label": "Submit"},
    }
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop.confirmed_plan_by_step_id = {
        "step-1": {
            "step_id": "step-1",
            "step_number": 1,
            "parent_intent": step_context["intent"],
            "expected_outcome": step_context["expected_outcome"],
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert",
                    "target": "Submit",
                    "locator": 'get_by_label("Submit")',
                    "assertion": "visible",
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": "Assert Submit is visible",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}

    blocked_result = loop._validate_confirmed_execution_tool_call(
        "action_assert",
        {
            "locator": 'get_by_role("button", name="Submit")',
            "assertion": "visible",
        },
    )

    assert blocked_result["blocked"] is True
    assert blocked_result["reason"] == "execution_contract_mismatch"


def test_canonicalize_assertion_operation_prefers_exact_text_for_generic_main_locator() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    step_context["intent"] = "Assert Playwright Test Agents is visible"
    step_context["element_name"] = "Playwright Test Agents"
    step_context["element_info"] = {
        "text": "Playwright Test Agents",
        "attributes": {"aria-label": "Playwright Test Agents"},
    }

    child = loop._canonicalize_assertion_operation(
        {
            "type": "assert",
            "target": "Playwright Test Agents",
            "locator": "main",
            "assertion": "visible",
        },
        source_step=step_context,
    )

    assert child["assertion"] == "visible"
    assert child["target"] == "Playwright Test Agents"
    assert child["description"] == "Playwright Test Agents is visible"
    assert child["locator"] == 'get_by_text("Playwright Test Agents", exact=True)'


def test_canonicalize_visible_assertion_prefers_locator_hint_over_broad_source_text() -> None:
    loop = _make_loop()
    specific_target = "Playwright Test Agents"
    broad_page_text = "PLAYWRIGHT GUIDE / LOCAL DOCS Playwright Test Agents docs landing page"
    step_context = _make_step_context()
    step_context["intent"] = f"Assert {specific_target} is visible"
    step_context["element_name"] = broad_page_text
    step_context["element_info"] = {
        "text": broad_page_text,
        "attributes": {"aria-label": broad_page_text},
    }

    child = loop._canonicalize_assertion_operation(
        {
            "type": "assert",
            "target": broad_page_text,
            "locator": f'get_by_text("{specific_target}", exact=True)',
            "assertion": "visible",
        },
        source_step=step_context,
    )

    assert child["assertion"] == "visible"
    assert child["target"] == specific_target
    assert child["description"] == f"{specific_target} is visible"
    assert child["locator"] == f'get_by_text("{specific_target}", exact=True)'


def test_canonicalize_visible_assertion_prefers_source_locator_over_broad_child_locator() -> None:
    loop = _make_loop()
    specific_target = "Playwright Test Agents"
    broad_page_text = "PLAYWRIGHT GUIDE / LOCAL DOCS Playwright Test Agents docs landing page"
    step_context = _make_step_context()
    step_context["intent"] = f"Assert {specific_target} is visible"
    step_context["element_name"] = broad_page_text
    step_context["element_info"] = {
        "text": broad_page_text,
        "attributes": {"aria-label": broad_page_text},
    }
    step_context["locator"] = f'get_by_text("{specific_target}", exact=True)'

    child = loop._canonicalize_assertion_operation(
        {
            "type": "assert",
            "target": broad_page_text,
            "locator": f'get_by_text("{broad_page_text}", exact=True)',
            "assertion": "visible",
        },
        source_step=step_context,
    )

    assert child["assertion"] == "visible"
    assert child["target"] == specific_target
    assert child["description"] == f"{specific_target} is visible"
    assert child["locator"] == f'get_by_text("{specific_target}", exact=True)'


def test_confirmed_visible_assertion_keeps_specific_target_and_emits_code_update_when_source_text_is_broader() -> None:
    loop = _make_loop()
    specific_target = "Playwright Test Agents"
    broad_page_text = "PLAYWRIGHT GUIDE / LOCAL DOCS Playwright Test Agents docs landing page"
    specific_locator = f'get_by_text("{specific_target}", exact=True)'
    expected_line = (
        f'await expect(page.getByText("{specific_target}", {{ exact: true }})).'
        f'toBeVisible();'
    )

    step_context = _make_step_context()
    step_context["intent"] = f"Assert {specific_target} is visible"
    step_context["element_name"] = broad_page_text
    step_context["element_info"] = {
        "text": broad_page_text,
        "attributes": {"aria-label": broad_page_text},
    }

    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "step-1"
    loop.plan_confirmed = True
    loop._active_plan_state = {
        "plan_id": "plan-1",
        "summary": f"Assert {specific_target} is visible",
        "original_user_intent": step_context["intent"],
        "steps": [dict(step_context)],
    }
    loop._store_confirmed_execution_plan(
        {
            "plan_id": "plan-1",
            "summary": f"Assert {specific_target} is visible",
            "original_user_intent": step_context["intent"],
            "steps": [
                {
                    "step_id": "step-1",
                    "step_number": 1,
                    "intent": step_context["intent"],
                    "expected_outcome": step_context["expected_outcome"],
                    "children": [
                        {
                            "operation_id": "op_1",
                            "type": "assert",
                            "target": specific_target,
                            "locator": "main",
                            "assertion": "visible",
                            "status": "planned",
                        }
                    ],
                }
            ],
        }
    )

    allowed_result = loop._validate_confirmed_execution_tool_call(
        "action_assert",
        {
            "locator": specific_locator,
            "assertion": "visible",
        },
    )

    assert allowed_result["allowed"] is True
    assert allowed_result["expected_child"]["type"] == "assert"
    assert allowed_result["expected_child"]["assertion"] == "visible"
    assert allowed_result["expected_child"]["target"] == specific_target
    assert allowed_result["expected_child"]["locator"] == specific_locator

    success_record = loop._record_confirmed_execution_child_result(
        step_context,
        allowed_result["expected_child"],
        tool_name="action_assert",
        args={
            "locator": specific_locator,
            "assertion": "visible",
        },
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
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[1][0] == "code_update"

    step_recorded_payload = sent_messages[0][1]
    code_update_payload = sent_messages[1][1]
    recorded_child = step_recorded_payload["children"][0]

    assert step_recorded_payload["expected_outcome"] == step_context["expected_outcome"]
    assert recorded_child["type"] == "assert"
    assert recorded_child["assertion"] == "visible"
    assert recorded_child["target"] == specific_target
    assert recorded_child["locator"] == specific_locator
    assert "expected_outcome" not in recorded_child
    assert recorded_child["code_lines"] == [expected_line]
    assert code_update_payload["lines"] == [expected_line]
    assert code_update_payload["full_spec_preview"] == expected_line
    assert specific_target in code_update_payload["full_spec_preview"]
    assert broad_page_text not in code_update_payload["full_spec_preview"]


def test_confirmed_execution_context_message_requires_exact_child_locator() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop.confirmed_plan_by_step_id = {
        "step-1": {
            "step_id": "step-1",
            "step_number": 1,
            "parent_intent": step_context["intent"],
            "expected_outcome": step_context["expected_outcome"],
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert",
                    "target": "Submit",
                    "locator": 'main',
                    "assertion": "visible",
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": "Check Submit is visible",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}

    context_message = loop._build_confirmed_execution_context_message()

    assert "Use the confirmed child locator exactly as written." in context_message
    assert "Do not swap a confirmed locator for a different equivalent locator during retries." in context_message


def test_step_recorded_payload_advances_confirmed_cursor_and_keeps_step_two_assert_isolated() -> None:
    loop = _make_loop()
    raw_steps = [
        {
            "id": "step-1",
            "intent": "Click the first button",
            "element_info": {
                "text": "First",
                "attributes": {"aria-label": "First"},
            },
            "expected_outcome": {
                "type": "navigation",
                "description": "goes to the first page",
                "source": "user",
                "required": True,
            },
        },
        {
            "id": "step-2",
            "intent": "Assert the second label is visible",
            "element_info": {
                "text": "Second",
                "attributes": {"aria-label": "Second"},
            },
            "expected_outcome": {
                "type": "no_visible_change",
                "description": "stays on the current page",
                "source": "user",
                "required": False,
            },
        },
    ]
    loop._prepare_recording_steps(raw_steps)

    step_one = loop.step_state_by_id["step-1"]
    step_two = loop.step_state_by_id["step-2"]
    step_one_click_record = _make_action_record(
        step_one,
        "action_click",
        "click",
        'get_by_label("First")',
    )
    step_two_assert_record = _make_action_record(
        step_two,
        "action_assert",
        "assert",
        'get_by_label("Second")',
        assertion="visible",
    )
    loop._active_plan_state = {
        "plan_id": "plan-2",
        "summary": "Click first then assert second",
        "original_user_intent": "Click the first button and assert the second label",
        "steps": list(raw_steps),
    }
    loop._store_confirmed_execution_plan(
        {
            "plan_id": "plan-2",
            "summary": "Click first then assert second",
            "original_user_intent": "Click the first button and assert the second label",
            "steps": [
                {
                    "step_id": "step-1",
                    "step_number": 1,
                    "intent": step_one["intent"],
                    "expected_outcome": step_one["expected_outcome"],
                    "children": [
                        _make_planned_child(
                            "op_1",
                            "click",
                            "First",
                            target="First",
                            locator='get_by_label("First")',
                        ),
                    ],
                },
                {
                    "step_id": "step-2",
                    "step_number": 2,
                    "intent": step_two["intent"],
                    "expected_outcome": step_two["expected_outcome"],
                    "children": [
                        _make_planned_child(
                            "op_1",
                            "assert",
                            "Second is visible",
                            target="Second",
                            locator='get_by_label("Second")',
                            assertion="visible",
                        ),
                    ],
                },
            ],
        }
    )
    loop.successful_action_by_step_id = {
        "step-1": step_one_click_record,
        "step-2": step_two_assert_record,
    }
    loop.successful_actions_by_step_id = {
        "step-1": [step_one_click_record],
        "step-2": [step_two_assert_record],
    }
    loop.last_successful_action = step_one_click_record
    loop._mark_step_recorded(
        step_one,
        {
            "step_number": 1,
            "action": "click",
            "locator": 'get_by_label("First")',
        },
    )

    confirmed_cursor = loop._current_confirmed_execution_cursor()

    assert confirmed_cursor["step_id"] == "step-2"
    assert confirmed_cursor["next_child"]["type"] == "assert"

    loop.confirmed_child_results_by_step_id["step-2"] = {
        "op_1": {**step_two_assert_record, "status": "success"},
    }

    payload = loop._build_step_record_payload(
        {
            "step_id": "step-2",
            "step_number": 2,
        },
        step_two,
    )

    assert payload["step_id"] == "step-2"
    assert payload["step_number"] == 2
    assert payload["action"] == "assert"
    assert payload["locator"] == 'get_by_label("Second")'
    assert payload["generated_line"].startswith("await expect(")
    assert [child["type"] for child in payload["children"]] == ["assert"]
    assert [child["code_lines"][0].startswith("await expect(") for child in payload["children"]] == [True]


def test_blocked_mismatch_cannot_later_become_click_only_success() -> None:
    loop = _make_loop()
    raw_steps = [
        {
            "id": "step-1",
            "intent": "Click the first button",
            "element_info": {
                "text": "First",
                "attributes": {"aria-label": "First"},
            },
            "expected_outcome": {
                "type": "navigation",
                "description": "goes to the first page",
                "source": "user",
                "required": True,
            },
        },
        {
            "id": "step-2",
            "intent": "Assert the second label is visible",
            "element_info": {
                "text": "Second",
                "attributes": {"aria-label": "Second"},
            },
            "expected_outcome": {
                "type": "no_visible_change",
                "description": "stays on the current page",
                "source": "user",
                "required": False,
            },
        },
        {
            "id": "step-3",
            "intent": "Click the third button",
            "element_info": {
                "text": "Third",
                "attributes": {"aria-label": "Third"},
            },
            "expected_outcome": {
                "type": "navigation",
                "description": "goes to the third page",
                "source": "user",
                "required": True,
            },
        },
    ]
    loop._prepare_recording_steps(raw_steps)

    step_one = loop.step_state_by_id["step-1"]
    step_two = loop.step_state_by_id["step-2"]
    step_three = loop.step_state_by_id["step-3"]
    step_one_click_record = _make_action_record(
        step_one,
        "action_click",
        "click",
        'get_by_label("First")',
    )
    step_three_click_record = _make_action_record(
        step_three,
        "action_click",
        "click",
        'get_by_label("Third")',
    )
    loop._active_plan_state = {
        "plan_id": "plan-3",
        "summary": "Click first then assert second",
        "original_user_intent": "Click the first button and assert the second label",
        "steps": list(raw_steps),
    }
    loop._store_confirmed_execution_plan(
        {
            "plan_id": "plan-3",
            "summary": "Click first then assert second",
            "original_user_intent": "Click the first button and assert the second label",
            "steps": [
                {
                    "step_id": "step-1",
                    "step_number": 1,
                    "intent": step_one["intent"],
                    "expected_outcome": step_one["expected_outcome"],
                    "children": [
                        _make_planned_child(
                            "op_1",
                            "click",
                            "First",
                            target="First",
                            locator='get_by_label("First")',
                        ),
                    ],
                },
                {
                    "step_id": "step-2",
                    "step_number": 2,
                    "intent": step_two["intent"],
                    "expected_outcome": step_two["expected_outcome"],
                    "children": [
                        _make_planned_child(
                            "op_1",
                            "assert",
                            "Second is visible",
                            target="Second",
                            locator='get_by_label("Second")',
                            assertion="visible",
                        ),
                    ],
                },
                {
                    "step_id": "step-3",
                    "step_number": 3,
                    "intent": step_three["intent"],
                    "expected_outcome": step_three["expected_outcome"],
                    "children": [
                        _make_planned_child(
                            "op_1",
                            "click",
                            "Third",
                            target="Third",
                            locator='get_by_label("Third")',
                        ),
                    ],
                },
            ],
        }
    )
    loop.successful_action_by_step_id = {
        "step-1": step_one_click_record,
        "step-3": step_three_click_record,
    }
    loop.successful_actions_by_step_id = {
        "step-1": [step_one_click_record],
        "step-3": [step_three_click_record],
    }
    loop.last_successful_action = step_three_click_record
    loop._mark_step_recorded(
        step_one,
        {
            "step_number": 1,
            "action": "click",
            "locator": 'get_by_label("First")',
        },
    )

    blocked_result = loop._validate_confirmed_execution_tool_call(
        "action_click",
        {
            "step_id": "step-2",
            "step_number": 2,
            "locator": 'get_by_label("Second")',
        },
    )

    assert blocked_result["blocked"] is True
    assert blocked_result["step_id"] == "step-2"
    assert blocked_result["expected_child"]["type"] == "assert"
    assert loop.confirmed_execution_mismatch_count_by_step_id["step-2"] == 1
    assert loop.last_successful_action["step_id"] == "step-3"
    assert "step-2" not in loop.successful_action_by_step_id

    loop.confirmed_child_results_by_step_id["step-2"] = {
        "op_1": {"status": "blocked"},
    }

    payload = loop._build_step_record_payload(
        {
            "step_id": "step-2",
            "step_number": 2,
        },
        step_two,
    )

    assert payload == {}


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
    assert len(sent_messages) == 3
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[1][0] == "code_update"
    assert sent_messages[2][0] == "run_completed"

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
