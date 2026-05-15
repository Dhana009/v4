from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import agent as agent_module

from tests.test_planning_through_controller_fake_model import (
    _install_common_run_stubs,
    _make_agent_loop,
    _make_content_only_response,
    _make_current_step,
)


def test_recovery_diagnoser_run_uses_controller_and_compact_context(monkeypatch) -> None:
    loop = _make_agent_loop()
    sent_messages: list[tuple[str, dict[str, Any]]] = []
    controller_calls: list[dict[str, Any]] = []
    loop.current_steps = [_make_current_step()]
    _install_common_run_stubs(loop, sent_messages)
    loop.tools = [
        {"type": "function", "function": {"name": "browser_get_state"}},
        {"type": "function", "function": {"name": "ask_user"}},
        {"type": "function", "function": {"name": "action_click"}},
    ]

    def fake_reset_lifecycle_state(steps=None):
        loop.phase = "recovering"
        loop.plan_confirmed = False
        loop.current_steps = list(steps or [])
        loop.phase_tracker.current_phase = "recovery"
        loop.step_state_by_id = {
            "step-1": {
                "step_id": "step-1",
                "status": "recovery_pending",
                "last_error": "timeout while clicking",
                "operation_id": "op-1",
                "step_number": 1,
                "intent": "Click the Get started button",
            }
        }
        loop.step_context_by_id = dict(loop.step_state_by_id)
        loop.active_step_id = "step-1"
        loop.active_failed_step_id = "step-1"
        loop.pending_recovery = True
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
        loop.run_stop_requested = True
        loop._llm_call_counter = 0
        loop.confirmed_plan_by_step_id = {}
        loop.confirmed_plan_step_ids = []
        loop.confirmed_child_results_by_step_id = {}
        loop.confirmed_execution_mismatch_count_by_step_id = {}
        loop._clear_plan_review_context()
        loop._clear_active_plan_state()

    async def fake_controller_call(**kwargs: Any) -> dict[str, Any]:
        controller_calls.append(dict(kwargs))
        response = _make_content_only_response(
            '{"purpose":"recovery_diagnoser","schema_id":"recovery_diagnoser.v1","recovery_action":"retry","requires_user_confirmation":false}'
        )
        return {
            "used_controller": True,
            "validation_status": "raw_response_preserved",
            "raw_response": response,
            "raw_message": response.choices[0].message,
            "content": response.choices[0].message.content,
            "tool_calls": [],
        }

    async def fake_router_call(**kwargs: Any) -> Any:
        raise AssertionError("model_router.call should not be used for recovery_diagnoser")

    async def fake_try_deterministic_fast_path(steps: list[dict[str, Any]]) -> bool:
        return False

    class FakePage:
        url = "http://fixture/current"

        async def title(self) -> str:
            return "Fixture page"

    loop._reset_lifecycle_state = fake_reset_lifecycle_state
    loop._load_phase_skill_expansion = lambda phase: []
    loop._try_deterministic_fast_path = fake_try_deterministic_fast_path
    loop._current_phase = lambda: "recovery"
    loop._all_steps_done = lambda: True
    loop._has_unresolved_failure = lambda: False
    loop._should_request_user_followup = lambda *args, **kwargs: False
    loop._llm_runtime_controller = SimpleNamespace(call_with_raw_response=fake_controller_call)
    loop.model_router = SimpleNamespace(call=fake_router_call)

    monkeypatch.setattr(agent_module, "get_page", lambda: FakePage())
    monkeypatch.setattr(agent_module, "record_model_call_start", lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(agent_module, "record_model_call_end", lambda *args, **kwargs: None)

    asyncio.run(loop.run([_make_current_step()]))

    assert controller_calls
    assert controller_calls[0]["purpose"] == "recovery_diagnoser"
    tool_names = [tool["function"]["name"] for tool in controller_calls[0]["tools"]]
    assert tool_names == ["browser_get_state", "ask_user"]
    serialized_messages = "\n".join(
        str(message.get("content") or "") for message in controller_calls[0]["messages"]
    )
    assert "DYNAMIC_RECOVERY_CONTEXT:" in serialized_messages
    assert "Recovery required for the failed original step." in serialized_messages
    assert "timeout while clicking" in serialized_messages
    assert "http://fixture/current" in serialized_messages
    assert "Fixture page" in serialized_messages
    _INFRA = {"run_started", "step_validating", "step_executing", "step_failed", "step_skipped"}
    msgs = [m for m in sent_messages if m[0] not in _INFRA]
    assert msgs[-1][0] == "llm_result"
