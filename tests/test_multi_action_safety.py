from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import agent as agent_module
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


def _make_step_context(
    step_id: str,
    intent: str,
    element_text: str,
    aria_label: str,
    expected_outcome: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "step_id": step_id,
        "step_number": 1,
        "intent": intent,
        "element_info": {
            "text": element_text,
            "attributes": {"aria-label": aria_label},
        },
        "element_name": element_text,
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


def _make_tool_call(call_id: str, name: str, arguments: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


def _build_loop_for_multi_action_safety_test(
    monkeypatch,
    step_context: dict[str, object],
    tool_calls: list[SimpleNamespace],
    responses: list[SimpleNamespace] | None = None,
):
    sent_messages: list[tuple[str, dict[str, object]]] = []
    blocked_results: list[tuple[str, dict[str, object]]] = []
    executed_actions: list[str] = []
    call_counter = {"count": 0}

    loop = AgentLoop.__new__(AgentLoop)
    loop.ws = object()
    loop.control_queue = object()
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = "idle"
    original_set_phase = loop.phase_tracker.set_phase

    def recording_set_phase(new_phase, reason=None, step_id=None):
        return original_set_phase(new_phase, reason=reason, step_id=step_id)

    loop.phase_tracker.set_phase = recording_set_phase
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

    def fake_reset_lifecycle_state(steps=None):
        if steps is None:
            return
        loop.phase = "planning"
        loop.plan_confirmed = True
        loop.current_steps = list(steps)
        loop.phase_tracker.current_phase = "idle"
        loop.step_state_by_id = {"step-1": step_context}
        loop.step_context_by_id = {"step-1": step_context}
        loop.active_step_id = "step-1"
        loop.active_failed_step_id = None
        loop.pending_recovery = False
        loop.completed_step_ids = set()
        loop.skipped_step_ids = set()
        loop.current_step_index = 0
        loop.last_successful_action = None
        loop.successful_action_by_step_id = {}
        loop.successful_actions_by_step_id = {}
        loop._recording_steps = [step_context]
        loop._recording_step_index = 0
        loop._recorded_step_ids = set()
        loop._last_action_context = None
        loop._awaiting_step_record = False
        loop._pending_failure_followup = False
        loop._run_completion_requested = False
        loop.run_stop_requested = False
        loop._llm_call_counter = 0
        loop.confirmed_plan_by_step_id = {}
        loop.confirmed_plan_step_ids = []
        loop.confirmed_child_results_by_step_id = {}
        loop.confirmed_execution_mismatch_count_by_step_id = {}

    loop._reset_lifecycle_state = fake_reset_lifecycle_state
    loop._prepare_recording_steps = lambda steps: None
    loop._load_skills_for_steps = lambda steps: (["core"], "", [{"name": "core"}])
    loop._load_phase_skill_expansion = lambda phase: []

    async def fake_send(msg_type, **kwargs):
        sent_messages.append((msg_type, kwargs))

    loop._send = fake_send

    original_append_tool_response = loop._append_tool_response

    def recording_append_tool_response(tool_call_id, result):
        blocked_results.append((tool_call_id, result))
        return original_append_tool_response(tool_call_id, result)

    loop._append_tool_response = recording_append_tool_response

    async def fake_action_click(args):
        executed_actions.append("action_click")
        locator = str(args.get("locator") or "")
        return {"success": True, "error": None, "locator": locator}

    async def fake_action_assert(args):
        executed_actions.append("action_assert")
        locator = str(args.get("locator") or "")
        assertion = str(args.get("assertion") or "visible")
        return {
            "success": True,
            "error": None,
            "locator": locator,
            "assertion": assertion,
        }

    loop._tool_action_click = fake_action_click
    loop._tool_action_assert = fake_action_assert

    response_queue = list(responses) if responses is not None else [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="", tool_calls=list(tool_calls))
                )
            ]
        )
    ]

    async def fake_model_call(*args, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] > len(response_queue):
            raise AssertionError("Unexpected second model call")
        return response_queue[call_counter["count"] - 1]

    loop.model_router = SimpleNamespace(call=fake_model_call)
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: object())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)
    return loop, sent_messages, blocked_results, executed_actions, call_counter


def test_single_click_action_can_still_be_recorded(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Click the submit button",
        "Submit",
        "Submit",
    )
    tool_calls = [
        _make_tool_call(
            "call-1",
            "action_click",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Submit")',
            },
        ),
    ]

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        tool_calls,
    )

    capture_calls: list[str] = []
    capture_states = [
        {
            "url": "https://playwright.dev/",
            "title": "Playwright",
        },
        {
            "url": "https://playwright.dev/docs/intro",
            "title": "Installation | Playwright",
        },
    ]
    capture_index = {"count": 0}

    async def fake_capture_browser_state() -> dict[str, str]:
        call_index = capture_index["count"]
        capture_index["count"] += 1
        capture_calls.append("capture")
        return capture_states[call_index]

    loop._capture_browser_state = fake_capture_browser_state

    asyncio.run(loop.run([step_context]))

    assert call_counter["count"] == 1
    assert executed_actions == ["action_click"]
    assert capture_calls == ["capture", "capture"]
    assert capture_index["count"] == 2
    assert blocked_results == []
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[0][1]["action"] == "click"
    assert sent_messages[0][1]["status"] == "success"
    assert sent_messages[0][1]["observed_outcome"] == {
        "type": "navigation",
        "before_url": "https://playwright.dev/",
        "after_url": "https://playwright.dev/docs/intro",
        "before_title": "Playwright",
        "after_title": "Installation | Playwright",
        "matched_expected": True,
    }
    assert sent_messages[0][1]["children"][0]["type"] == "click"
    assert sent_messages[1][0] == "code_update"
    assert sent_messages[1][1]["lines"] == [sent_messages[0][1]["generated_line"]]


def test_assert_and_click_both_execute_and_record_in_order(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Check that Get started is visible and click it",
        "Get started",
        "Get started",
    )
    tool_calls = [
        _make_tool_call(
            "call-1",
            "action_assert",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Get started")',
                "assertion": "visible",
            },
        ),
        _make_tool_call(
            "call-2",
            "action_click",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Get started")',
            },
        ),
    ]

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        tool_calls,
    )

    asyncio.run(loop.run([step_context]))

    assert call_counter["count"] == 1
    assert executed_actions == ["action_assert", "action_click"]
    assert blocked_results == []
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert len(sent_messages[0][1]["children"]) == 2
    assert sent_messages[0][1]["action"] == "click"
    assert sent_messages[0][1]["status"] == "success"
    assert sent_messages[0][1]["children"][0]["type"] == "assert"
    assert sent_messages[0][1]["children"][1]["type"] == "click"
    assert sent_messages[1][0] == "code_update"
    assert len(sent_messages[1][1]["lines"]) == 2


def test_confirmed_execution_contract_blocks_wrong_assertion_and_allows_correct_sequence(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Check that Get started is visible and click it",
        "Get started",
        "Get started",
    )
    wrong_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        _make_tool_call(
                            "call-1",
                            "action_assert",
                            {
                                "step_id": "step-1",
                                "step_number": 1,
                                "locator": "page.title",
                                "assertion": "has_text",
                                "expected_value": "Fast and reliable...",
                            },
                        )
                    ],
                )
            )
        ]
    )
    correct_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        _make_tool_call(
                            "call-2",
                            "action_assert",
                            {
                                "step_id": "step-1",
                                "step_number": 1,
                                "locator": 'get_by_label("Get started")',
                                "assertion": "visible",
                            },
                        ),
                        _make_tool_call(
                            "call-3",
                            "action_click",
                            {
                                "step_id": "step-1",
                                "step_number": 1,
                                "locator": 'get_by_label("Get started")',
                            },
                        ),
                    ],
                )
            )
        ]
    )

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        [],
        responses=[wrong_response, correct_response],
    )
    original_reset = loop._reset_lifecycle_state

    def reset_with_confirmed_contract(steps=None):
        original_reset(steps)
        if steps is None:
            return
        loop.phase = "executing"
        loop.phase_tracker.current_phase = "executing"
        loop._active_plan_state = {
            "plan_id": "plan-1",
            "summary": "I will check and click Get started",
            "original_user_intent": step_context["intent"],
            "steps": [step_context],
        }
        loop._store_confirmed_execution_plan(
            {
                "plan_id": "plan-1",
                "summary": "I will check and click Get started",
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
                                "description": "Get started is visible",
                                "target": "Get started",
                                "locator": 'get_by_label("Get started")',
                                "status": "planned",
                                "assertion": "visible",
                            },
                            {
                                "operation_id": "op_2",
                                "type": "click",
                                "description": "Get started",
                                "target": "Get started",
                                "locator": 'get_by_label("Get started")',
                                "status": "planned",
                            },
                        ],
                    }
                ],
            }
        )

    loop._reset_lifecycle_state = reset_with_confirmed_contract

    asyncio.run(loop.run([step_context]))

    assert call_counter["count"] == 2
    assert executed_actions == ["action_assert", "action_click"]
    assert [tool_call_id for tool_call_id, _ in blocked_results] == ["call-1"]
    assert blocked_results[0][1]["reason"] == "execution_contract_mismatch"
    assert blocked_results[0][1]["skipped"] is True
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert [child["type"] for child in sent_messages[0][1]["children"]] == ["assert", "click"]
    assert [child["operation_id"] for child in sent_messages[0][1]["children"]] == ["op_1", "op_2"]
    assert len(sent_messages[1][1]["lines"]) == 2
    assert sent_messages[1][1]["lines"][0].startswith("await expect(")
    assert sent_messages[1][1]["lines"][1].endswith('.click();')


def test_auto_record_ends_batch_before_followup_model_turns(monkeypatch) -> None:
    step_context = _make_step_context(
        "pending-step-mooeb8ca-2",
        "Click the submit button",
        "Submit",
        "Submit",
    )
    responses = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            _make_tool_call(
                                "call-1",
                                "action_click",
                                {
                                    "step_id": "pending-step-mooeb8ca-2",
                                    "step_number": 1,
                                    "locator": 'get_by_label("Submit")',
                                },
                            )
                        ],
                    )
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            _make_tool_call(
                                "call-2",
                                "screenshot_take",
                                {"filename": "debug.png"},
                            )
                        ],
                    )
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            _make_tool_call(
                                "call-3",
                                "send_to_overlay",
                                {
                                    "message_type": "step_recorded",
                                    "payload": {
                                        "step_id": "1",
                                        "step_number": 1,
                                    },
                                },
                            )
                        ],
                    )
                )
            ]
        ),
    ]

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        [],
        responses=responses,
    )

    asyncio.run(loop.run([step_context]))

    assert call_counter["count"] == 1
    assert executed_actions == ["action_click"]
    assert blocked_results == []
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[0][1]["step_id"] == "pending-step-mooeb8ca-2"
    assert sent_messages[1][0] == "code_update"


def test_failed_assert_stops_later_click_in_same_batch(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Check that Get started is visible and click it",
        "Get started",
        "Get started",
    )
    tool_calls = [
        _make_tool_call(
            "call-1",
            "action_assert",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Get started")',
                "assertion": "visible",
            },
        ),
        _make_tool_call(
            "call-2",
            "action_click",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Get started")',
            },
        ),
        _make_tool_call(
            "call-3",
            "send_to_overlay",
            {
                "message_type": "step_recorded",
                "payload": {
                    "step_id": "step-1",
                    "step_number": 1,
                },
            },
        ),
    ]

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        tool_calls,
    )

    async def failing_action_assert(args):
        executed_actions.append("action_assert")
        locator = str(args.get("locator") or "")
        assertion = str(args.get("assertion") or "visible")
        return {
            "success": False,
            "error": "assertion failed",
            "locator": locator,
            "assertion": assertion,
        }

    async def fake_tool_ask_user(args):  # noqa: ARG001
        return {"answer": "stop", "event_type": "option_selected"}

    responses = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="", tool_calls=list(tool_calls))
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="Please advise how would you like to proceed",
                        tool_calls=[],
                    )
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="", tool_calls=[])
                )
            ]
        ),
    ]

    async def fake_model_call(*args, **kwargs):  # noqa: ARG001
        call_counter["count"] += 1
        if call_counter["count"] > len(responses):
            raise AssertionError("Unexpected extra model call")
        return responses[call_counter["count"] - 1]

    loop._tool_action_assert = failing_action_assert
    loop._tool_ask_user = fake_tool_ask_user
    loop.model_router = SimpleNamespace(call=fake_model_call)

    asyncio.run(loop.run([step_context]))

    assert call_counter["count"] == 3
    assert executed_actions == ["action_assert"]
    assert [tool_call_id for tool_call_id, _ in blocked_results] == ["call-2", "call-3"]
    assert blocked_results[0][1]["skipped"] is True
    assert blocked_results[0][1]["requires_replan"] is True
    assert sent_messages[-1][0] == "llm_result"


def test_failed_step_clears_stale_success_history_before_recording(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Click the submit button",
        "Submit",
        "Submit",
    )
    success_record = {
        "tool": "action_click",
        "action": "click",
        "locator": 'get_by_role("button", name="Submit")',
        "result": {"success": True, "skipped": False},
        "step_context": step_context,
        "action_context": {"locator": 'get_by_role("button", name="Submit")'},
        "tool_args": {"locator": 'get_by_role("button", name="Submit")'},
        "step_id": step_context["step_id"],
        "step_number": step_context["step_number"],
    }
    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        [],
    )

    loop._recording_steps = [step_context]
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop._awaiting_step_record = True
    loop.last_successful_action = success_record
    loop.successful_action_by_step_id = {"step-1": success_record}
    loop.successful_actions_by_step_id = {"step-1": [success_record]}

    loop._mark_step_failed(step_context, "assertion failed")

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
    assert loop.last_successful_action is None
    assert loop.successful_action_by_step_id == {}
    assert loop.successful_actions_by_step_id == {}
    assert loop._last_action_context is None
    assert sent_messages == []
    assert blocked_results == []
    assert executed_actions == []
    assert call_counter["count"] == 0


def test_click_like_step_without_expected_outcome_is_blocked_before_llm(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Click the submit button",
        "Submit",
        "Submit",
    )
    step_context.pop("expected_outcome", None)

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        [],
    )

    asyncio.run(loop.run([step_context]))

    assert call_counter["count"] == 0
    assert executed_actions == []
    assert blocked_results == []
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "error"
    assert "expected_outcome.type" in sent_messages[0][1]["message"]


def test_non_click_step_can_omit_expected_outcome(monkeypatch) -> None:
    step_context = _make_step_context(
        "step-1",
        "Assert the hero text is visible",
        "Hero",
        "Hero",
    )
    step_context.pop("expected_outcome", None)

    tool_calls = [
        _make_tool_call(
            "call-1",
            "action_assert",
            {
                "step_id": "step-1",
                "step_number": 1,
                "locator": 'get_by_label("Hero")',
                "assertion": "visible",
            },
        ),
    ]

    loop, sent_messages, blocked_results, executed_actions, call_counter = _build_loop_for_multi_action_safety_test(
        monkeypatch,
        step_context,
        tool_calls,
    )

    asyncio.run(loop.run([step_context]))

    assert call_counter["count"] == 1
    assert executed_actions == ["action_assert"]
    assert blocked_results == []
    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "step_recorded"
    assert sent_messages[0][1]["action"] == "assert"
    assert sent_messages[0][1]["status"] == "success"
    assert sent_messages[0][1]["children"][0]["type"] == "assert"
    assert sent_messages[1][0] == "code_update"
