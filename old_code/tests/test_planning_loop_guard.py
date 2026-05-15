from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from runtime.planning_loop_guard import (
    MAX_CONSECUTIVE_THINKING_ONLY_TURNS,
    MAX_PLANNING_TURNS_WITHOUT_TERMINAL_OUTPUT,
    PlanningLoopGuardState,
    advance_planning_loop_guard,
)


def _send_to_overlay_tool_call(call_id: str, message_type: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="send_to_overlay",
            arguments=json.dumps({"message_type": message_type, "payload": {"turn": call_id}}),
        ),
    )


def _ask_user_tool_call(call_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="ask_user",
            arguments=json.dumps({"question": "What should I do next?"}),
        ),
    )


def _action_click_tool_call(call_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="action_click",
            arguments=json.dumps({"locator": "get_by_text('Get started', exact=True)"}),
        ),
    )


def _browser_get_state_tool_call(call_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="browser_get_state",
            arguments=json.dumps({}),
        ),
    )


def _assistant_message(*tool_calls: SimpleNamespace, content: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        content=content,
        tool_calls=list(tool_calls),
        role="assistant",
    )


def test_repeated_llm_thinking_counts_as_no_terminal_progress() -> None:
    state = PlanningLoopGuardState()
    result_one = advance_planning_loop_guard(
        state,
        _assistant_message(_send_to_overlay_tool_call("call-1", "llm_thinking")),
        purpose="step_plan_normalizer",
    )
    result_two = advance_planning_loop_guard(
        result_one.state,
        _assistant_message(_send_to_overlay_tool_call("call-2", "llm_thinking")),
        purpose="step_plan_normalizer",
    )
    result_three = advance_planning_loop_guard(
        result_two.state,
        _assistant_message(_send_to_overlay_tool_call("call-3", "llm_thinking")),
        purpose="step_plan_normalizer",
    )

    assert result_one.should_stop is False
    assert result_one.state.consecutive_thinking_only_turns == 1
    assert result_one.state.planning_turns_without_terminal_output == 1
    assert result_one.inspection.thinking_only is True
    assert result_one.inspection.terminal_reason is None

    assert result_two.should_stop is False
    assert result_two.state.consecutive_thinking_only_turns == 2
    assert result_two.state.planning_turns_without_terminal_output == 2

    assert result_three.should_stop is True
    assert result_three.reason_code == "PLANNING_NO_PROGRESS"
    assert result_three.state.consecutive_thinking_only_turns == MAX_CONSECUTIVE_THINKING_ONLY_TURNS + 1
    assert result_three.state.planning_turns_without_terminal_output == 3
    assert result_three.message == "Planning did not produce plan_ready or clarification."
    assert "purpose=step_plan_normalizer" in str(result_three.detail or "")


def test_plan_ready_resets_or_satisfies_progress() -> None:
    state = PlanningLoopGuardState(consecutive_thinking_only_turns=2, planning_turns_without_terminal_output=2)
    result = advance_planning_loop_guard(
        state,
        _assistant_message(_send_to_overlay_tool_call("call-1", "plan_ready")),
        purpose="step_plan_normalizer",
    )

    assert result.should_stop is False
    assert result.state.consecutive_thinking_only_turns == 0
    assert result.state.planning_turns_without_terminal_output == 0
    assert result.inspection.terminal_reason == "plan_ready"
    assert result.inspection.thinking_only is False


@pytest.mark.parametrize(
    ("tool_call", "expected_terminal_reason"),
    [
        (_ask_user_tool_call("call-1"), "ask_user"),
        (_send_to_overlay_tool_call("call-2", "clarification_needed"), "clarification_needed"),
    ],
)
def test_ask_user_or_clarification_satisfies_progress(
    tool_call: SimpleNamespace,
    expected_terminal_reason: str,
) -> None:
    state = PlanningLoopGuardState(consecutive_thinking_only_turns=1, planning_turns_without_terminal_output=1)
    result = advance_planning_loop_guard(
        state,
        _assistant_message(tool_call),
        purpose="step_plan_normalizer",
    )

    assert result.should_stop is False
    assert result.state.consecutive_thinking_only_turns == 0
    assert result.state.planning_turns_without_terminal_output == 0
    assert result.inspection.terminal_reason == expected_terminal_reason
    assert result.inspection.thinking_only is False


def test_browser_action_before_confirmation_is_not_allowed_as_progress() -> None:
    state = PlanningLoopGuardState()
    result = advance_planning_loop_guard(
        state,
        _assistant_message(_action_click_tool_call("call-1")),
        purpose="step_plan_normalizer",
    )

    assert result.should_stop is False
    assert result.state.consecutive_thinking_only_turns == 0
    assert result.state.planning_turns_without_terminal_output == 1
    assert result.inspection.terminal_reason is None
    assert result.inspection.thinking_only is False
    assert "action_click" in result.inspection.tool_names


def test_no_success_lifecycle_on_no_progress() -> None:
    state = PlanningLoopGuardState()
    for turn_index in range(MAX_PLANNING_TURNS_WITHOUT_TERMINAL_OUTPUT):
        result = advance_planning_loop_guard(
            state,
            _assistant_message(_browser_get_state_tool_call(f"call-{turn_index + 1}")),
            purpose="step_plan_normalizer",
        )
        state = result.state

    assert result.should_stop is False

    final_result = advance_planning_loop_guard(
        state,
        _assistant_message(_browser_get_state_tool_call("call-final")),
        purpose="step_plan_normalizer",
    )

    assert final_result.should_stop is True
    assert final_result.reason_code == "PLANNING_NO_PROGRESS"
    assert final_result.state.planning_turns_without_terminal_output == MAX_PLANNING_TURNS_WITHOUT_TERMINAL_OUTPUT + 1
    assert final_result.state.consecutive_thinking_only_turns == 0
    assert final_result.inspection.terminal_reason is None
