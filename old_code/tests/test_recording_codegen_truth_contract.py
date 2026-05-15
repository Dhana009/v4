from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

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
    loop._active_plan_state = None
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


def test_step_recording_requires_backend_action_evidence_before_truth_is_recorded() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop._active_plan_state = {
        "plan_id": "plan-1",
        "summary": "I will check and click Get started",
        "original_user_intent": step_context["intent"],
        "steps": [deepcopy(step_context)],
    }

    async def _unexpected_send(message_type: str, **kwargs: object) -> None:  # noqa: ARG001
        raise AssertionError("step_recorded must not emit without backend evidence")

    loop._send = _unexpected_send

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

    assert result == {
        "sent": False,
        "skipped": True,
        "reason": "No successful confirmed action to record.",
    }


def test_recorded_step_keeps_expected_outcome_as_parent_metadata_and_excludes_child_targets() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
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
        "steps": [deepcopy(step_context)],
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

    assert payload["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    assert [child["operation_id"] for child in payload["children"]] == ["op_1", "op_2"]
    assert all("expected_outcome" not in child for child in payload["children"])
    assert all("observed_outcome" not in child for child in payload["children"])


def test_recorded_child_operation_order_matches_confirmed_execution_evidence() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
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
        "steps": [deepcopy(step_context)],
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

    assert [child["type"] for child in payload["children"]] == ["assert", "click"]
    assert [child["operation_id"] for child in payload["children"]] == ["op_1", "op_2"]
    assert code_update_payload["lines"] == [line for child in payload["children"] for line in child["code_lines"]]
    assert code_update_payload["full_spec_preview"] == "\n".join(code_update_payload["lines"])


def test_recorded_assert_child_preserves_value_alias_in_code_update_lines() -> None:
    loop = _make_loop()
    exact_text = "Fast and reliable docs"
    exact_locator = f'get_by_text("{exact_text}", exact=True)'
    step_context = _make_step_context()
    step_context["intent"] = f"Assert exact text equal to {exact_text}"
    step_context["element_name"] = exact_text
    step_context["element_info"] = {
        "text": exact_text,
        "attributes": {"aria-label": exact_text},
    }

    assert_result = {
        "operation_id": "op_1",
        "step_id": "step-1",
        "step_number": 1,
        "type": "assert",
        "target": exact_text,
        "locator": exact_locator,
        "assertion": "has_text",
        "status": "success",
        "tool": "action_assert",
        "action": "assert",
        "action_context": {
            "locator": exact_locator,
            "assertion": "has_text",
            "value": exact_text,
        },
        "tool_args": {
            "locator": exact_locator,
            "assertion": "has_text",
            "value": exact_text,
        },
        "result": {"success": True, "skipped": False},
    }

    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "step-1"
    loop.plan_confirmed = True
    loop._active_plan_state = {
        "plan_id": "plan-1",
        "summary": f"Assert exact text equal to {exact_text}",
        "original_user_intent": step_context["intent"],
        "steps": [deepcopy(step_context)],
    }
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
                    "assertion": "has_text",
                    "value": exact_text,
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": f"Assert exact text equal to {exact_text}",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {"op_1": assert_result}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}
    loop.last_successful_action = assert_result
    loop.successful_action_by_step_id = {"step-1": assert_result}
    loop.successful_actions_by_step_id = {"step-1": [assert_result]}

    payload = loop._build_step_record_payload(
        {
            "step_id": "step-1",
            "step_number": 1,
        },
        step_context,
    )
    code_update_payload = loop._build_code_update_payload(payload, "step-1")

    expected_line = (
        f'await expect(page.getByText("{exact_text}", {{ exact: true }})).'
        f'toContainText("{exact_text}");'
    )

    assert payload["children"][0]["assertion"] == "has_text"
    assert payload["children"][0]["value"] == exact_text
    assert payload["children"][0]["expected_value"] == exact_text
    assert payload["children"][0]["code_lines"] == [expected_line]
    assert code_update_payload["lines"] == [expected_line]
    assert code_update_payload["full_spec_preview"] == expected_line


def test_recorded_assert_child_preserves_expected_value_only_in_code_update_lines() -> None:
    loop = _make_loop()
    exact_text = "Fast and reliable docs"
    exact_locator = f'get_by_text("{exact_text}", exact=True)'
    step_context = _make_step_context()
    step_context["intent"] = f"Assert exact text equal to {exact_text}"
    step_context["element_name"] = exact_text
    step_context["element_info"] = {
        "text": exact_text,
        "attributes": {"aria-label": exact_text},
    }

    assert_result = {
        "operation_id": "op_1",
        "step_id": "step-1",
        "step_number": 1,
        "type": "assert",
        "target": exact_text,
        "locator": exact_locator,
        "assertion": "has_text",
        "status": "success",
        "tool": "action_assert",
        "action": "assert",
        "action_context": {
            "locator": exact_locator,
            "assertion": "has_text",
            "expected_value": exact_text,
        },
        "tool_args": {
            "locator": exact_locator,
            "assertion": "has_text",
            "expected_value": exact_text,
        },
        "result": {"success": True, "skipped": False},
    }

    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "step-1"
    loop.plan_confirmed = True
    loop._active_plan_state = {
        "plan_id": "plan-1",
        "summary": f"Assert exact text equal to {exact_text}",
        "original_user_intent": step_context["intent"],
        "steps": [deepcopy(step_context)],
    }
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
                    "assertion": "has_text",
                    "expected_value": exact_text,
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": f"Assert exact text equal to {exact_text}",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {"op_1": assert_result}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}
    loop.last_successful_action = assert_result
    loop.successful_action_by_step_id = {"step-1": assert_result}
    loop.successful_actions_by_step_id = {"step-1": [assert_result]}

    payload = loop._build_step_record_payload(
        {
            "step_id": "step-1",
            "step_number": 1,
        },
        step_context,
    )
    code_update_payload = loop._build_code_update_payload(payload, "step-1")

    expected_line = (
        f'await expect(page.getByText("{exact_text}", {{ exact: true }})).'
        f'toContainText("{exact_text}");'
    )

    assert payload["children"][0]["assertion"] == "has_text"
    assert payload["children"][0]["value"] == exact_text
    assert payload["children"][0]["expected_value"] == exact_text
    assert payload["children"][0]["code_lines"] == [expected_line]
    assert code_update_payload["lines"] == [expected_line]
    assert code_update_payload["full_spec_preview"] == expected_line


def test_recorded_assert_child_preserves_value_and_expected_value_in_code_update_lines() -> None:
    loop = _make_loop()
    exact_text = "Fast and reliable docs"
    exact_locator = f'get_by_text("{exact_text}", exact=True)'
    step_context = _make_step_context()
    step_context["intent"] = f"Assert exact text equal to {exact_text}"
    step_context["element_name"] = exact_text
    step_context["element_info"] = {
        "text": exact_text,
        "attributes": {"aria-label": exact_text},
    }

    assert_result = {
        "operation_id": "op_1",
        "step_id": "step-1",
        "step_number": 1,
        "type": "assert",
        "target": exact_text,
        "locator": exact_locator,
        "assertion": "has_text",
        "status": "success",
        "tool": "action_assert",
        "action": "assert",
        "action_context": {
            "locator": exact_locator,
            "assertion": "has_text",
            "value": exact_text,
            "expected_value": exact_text,
        },
        "tool_args": {
            "locator": exact_locator,
            "assertion": "has_text",
            "value": exact_text,
            "expected_value": exact_text,
        },
        "result": {"success": True, "skipped": False},
    }

    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.active_step_id = "step-1"
    loop.plan_confirmed = True
    loop._active_plan_state = {
        "plan_id": "plan-1",
        "summary": f"Assert exact text equal to {exact_text}",
        "original_user_intent": step_context["intent"],
        "steps": [deepcopy(step_context)],
    }
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
                    "assertion": "has_text",
                    "value": exact_text,
                    "expected_value": exact_text,
                    "status": "planned",
                }
            ],
            "plan_id": "plan-1",
            "summary": f"Assert exact text equal to {exact_text}",
            "original_user_intent": step_context["intent"],
        }
    }
    loop.confirmed_plan_step_ids = ["step-1"]
    loop.confirmed_child_results_by_step_id = {"step-1": {"op_1": assert_result}}
    loop.confirmed_execution_mismatch_count_by_step_id = {"step-1": 0}
    loop.last_successful_action = assert_result
    loop.successful_action_by_step_id = {"step-1": assert_result}
    loop.successful_actions_by_step_id = {"step-1": [assert_result]}

    payload = loop._build_step_record_payload(
        {
            "step_id": "step-1",
            "step_number": 1,
        },
        step_context,
    )
    code_update_payload = loop._build_code_update_payload(payload, "step-1")

    expected_line = (
        f'await expect(page.getByText("{exact_text}", {{ exact: true }})).'
        f'toContainText("{exact_text}");'
    )

    assert payload["children"][0]["assertion"] == "has_text"
    assert payload["children"][0]["value"] == exact_text
    assert payload["children"][0]["expected_value"] == exact_text
    assert code_update_payload["lines"] == [expected_line]
    assert code_update_payload["full_spec_preview"] == expected_line


def test_generated_assert_line_requires_text_for_has_text_and_has_value() -> None:
    loop = _make_loop()

    assert (
        loop._build_generated_line(
            "assert",
            'get_by_label("Submit")',
            {
                "locator": 'get_by_label("Submit")',
                "assertion": "has_text",
            },
        )
        == ""
    )
    assert (
        loop._build_generated_line(
            "assert",
            'get_by_label("Submit")',
            {
                "locator": 'get_by_label("Submit")',
                "assertion": "has_value",
            },
        )
        == ""
    )


def test_generated_assert_line_normalizes_single_quoted_locator_syntax() -> None:
    loop = _make_loop()
    exact_text = "Playwright Test Agents"
    single_quoted_locator = f"get_by_role('heading', name='{exact_text}')"

    line = loop._build_generated_line(
        "assert",
        single_quoted_locator,
        {
            "locator": single_quoted_locator,
            "assertion": "visible",
        },
    )

    assert line == f'await expect(page.getByRole("heading", {{ name: "{exact_text}" }})).toBeVisible();'


def test_code_update_payload_does_not_trust_generated_line_without_successful_child_evidence() -> None:
    loop = _make_loop()
    payload = {
        "step_id": "step-1",
        "step_number": 1,
        "generated_line": "LLM prose: click the submit button",
        "children": [
            {
                "operation_id": "op_1",
                "type": "assert",
                "status": "failed",
                "code_lines": [],
            },
            {
                "operation_id": "op_2",
                "type": "click",
                "status": "blocked",
                "code_lines": [],
            },
        ],
    }

    code_update_payload = loop._build_code_update_payload(payload, "step-1")

    assert code_update_payload == {}
