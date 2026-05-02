from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


class FakeQueue:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)


def _make_step_context() -> dict[str, object]:
    return {
        "step_id": "step-1",
        "step_number": 1,
        "intent": "Check that Get started is visible and click it",
        "element_info": {
            "text": "Get started",
            "attributes": {"aria-label": "Get started"},
        },
        "element_name": "Get started",
        "locator": None,
        "status": "recorded",
        "recorded": True,
        "last_error": None,
    }


def _make_assert_record(step_context: dict[str, object]) -> dict[str, object]:
    locator = 'get_by_label("Get started")'
    return {
        "tool": "action_assert",
        "action": "assert",
        "locator": locator,
        "result": {"success": True, "skipped": False},
        "step_context": step_context,
        "action_context": {
            "locator": locator,
            "assertion": "visible",
        },
        "tool_args": {
            "locator": locator,
            "assertion": "visible",
        },
        "step_id": step_context["step_id"],
        "step_number": step_context["step_number"],
    }


def _make_click_record(step_context: dict[str, object]) -> dict[str, object]:
    locator = 'get_by_label("Get started")'
    return {
        "tool": "action_click",
        "action": "click",
        "locator": locator,
        "result": {"success": True, "skipped": False},
        "step_context": step_context,
        "action_context": {
            "locator": locator,
        },
        "tool_args": {
            "locator": locator,
        },
        "step_id": step_context["step_id"],
        "step_number": step_context["step_number"],
    }


def _make_fill_record(step_context: dict[str, object]) -> dict[str, object]:
    locator = 'get_by_label("Search")'
    return {
        "tool": "action_fill",
        "action": "fill",
        "locator": locator,
        "result": {"success": True, "skipped": False},
        "step_context": step_context,
        "action_context": {
            "locator": locator,
            "value": "playwright",
        },
        "tool_args": {
            "locator": locator,
            "value": "playwright",
        },
        "step_id": step_context["step_id"],
        "step_number": step_context["step_number"],
    }


def _make_hover_record(step_context: dict[str, object]) -> dict[str, object]:
    locator = 'get_by_label("Get started")'
    return {
        "tool": "action_hover",
        "action": "hover",
        "locator": locator,
        "result": {"success": True, "skipped": False},
        "step_context": step_context,
        "action_context": {
            "locator": locator,
        },
        "tool_args": {
            "locator": locator,
        },
        "step_id": step_context["step_id"],
        "step_number": step_context["step_number"],
    }


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
    loop.capability_gaps = []
    loop.recorded_step_payloads = []
    loop.code_update_payloads = []
    loop.replay_recorded_step_payloads_by_step_id = {}
    loop.replay_action_history_by_step_id = {}
    loop._run_session_id = "run-test-001"
    loop._run_completion_requested = False
    loop.run_stop_requested = False
    loop._llm_call_counter = 0
    loop.llm = SimpleNamespace(
        messages=[],
        system_prompt="",
        client=object(),
        reset=lambda: None,
    )
    return loop


def test_replay_one_resolves_recorded_step_by_step_id_and_executes_operations_in_order() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    assert_record = _make_assert_record(step_context)
    click_record = _make_click_record(step_context)
    recorded_payload = {
        "step_id": "step-1",
        "step_number": 1,
        "intent": step_context["intent"],
        "action": "click",
        "element_name": "Get started",
        "locator": 'get_by_label("Get started")',
        "generated_line": "await getStarted.click();",
        "status": "success",
        "children": [
            {
                "operation_id": "op_1",
                "type": "assert",
                "description": "Get started is visible",
                "target": "Get started",
                "locator": 'get_by_label("Get started")',
                "status": "success",
                "code_lines": ["await expect(getStarted).toBeVisible();"],
            },
            {
                "operation_id": "op_2",
                "type": "click",
                "description": "Get started",
                "target": "Get started",
                "locator": 'get_by_label("Get started")',
                "status": "success",
                "code_lines": ["await getStarted.click();"],
            },
        ],
    }
    loop.replay_recorded_step_payloads_by_step_id = {"step-1": recorded_payload}
    loop.replay_action_history_by_step_id = {"step-1": [assert_record, click_record]}

    executed_actions: list[str] = []

    async def fake_assert(args: dict[str, object]) -> dict[str, object]:
        executed_actions.append("assert")
        assert str(args.get("locator") or "") == 'get_by_label("Get started")'
        assert str(args.get("assertion") or "") == "visible"
        return {"success": True, "error": None}

    async def fake_click(args: dict[str, object]) -> dict[str, object]:
        executed_actions.append("click")
        assert str(args.get("locator") or "") == 'get_by_label("Get started")'
        return {"success": True, "error": None}

    async def fake_fill(args: dict[str, object]) -> dict[str, object]:  # noqa: ARG001
        raise AssertionError("fill should not be called")

    loop._tool_action_assert = fake_assert
    loop._tool_action_click = fake_click
    loop._tool_action_fill = fake_fill

    result = asyncio.run(loop.replay_one("step-1"))

    assert result == {
        "type": "replay_one_result",
        "ok": True,
        "step_id": "step-1",
        "status": "success",
        "operation_count": 2,
    }
    assert executed_actions == ["assert", "click"]


def test_replay_one_supports_fill_operations() -> None:
    loop = _make_loop()
    step_context = {
        "step_id": "step-2",
        "step_number": 1,
        "intent": "Fill the search field",
        "element_info": {
            "text": "Search",
            "attributes": {"aria-label": "Search"},
        },
        "element_name": "Search",
        "locator": None,
        "status": "recorded",
        "recorded": True,
        "last_error": None,
    }
    fill_record = _make_fill_record(step_context)
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-2": {
            "step_id": "step-2",
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "fill",
                    "description": "Search: playwright",
                    "target": "Search",
                    "locator": 'get_by_label("Search")',
                    "status": "success",
                    "code_lines": ['await getByLabel("Search").fill("playwright");'],
                },
            ],
        }
    }
    loop.replay_action_history_by_step_id = {"step-2": [fill_record]}

    executed_actions: list[str] = []

    async def fake_fill(args: dict[str, object]) -> dict[str, object]:
        executed_actions.append("fill")
        assert str(args.get("locator") or "") == 'get_by_label("Search")'
        assert str(args.get("value") or "") == "playwright"
        return {"success": True, "error": None}

    loop._tool_action_fill = fake_fill

    result = asyncio.run(loop.replay_one("step-2"))

    assert result == {
        "type": "replay_one_result",
        "ok": True,
        "step_id": "step-2",
        "status": "success",
        "operation_count": 1,
    }
    assert executed_actions == ["fill"]


def test_replay_one_stops_on_first_failed_child_action() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    assert_record = _make_assert_record(step_context)
    click_record = _make_click_record(step_context)
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-1": {
            "step_id": "step-1",
            "children": [
                {"operation_id": "op_1", "type": "assert"},
                {"operation_id": "op_2", "type": "click"},
            ],
        }
    }
    loop.replay_action_history_by_step_id = {"step-1": [assert_record, click_record]}

    executed_actions: list[str] = []

    async def failing_assert(args: dict[str, object]) -> dict[str, object]:
        executed_actions.append("assert")
        return {"success": False, "error": "assertion failed"}

    async def forbidden_click(args: dict[str, object]) -> dict[str, object]:  # noqa: ARG001
        executed_actions.append("click")
        raise AssertionError("click should not be called after a failure")

    loop._tool_action_assert = failing_assert
    loop._tool_action_click = forbidden_click

    result = asyncio.run(loop.replay_one("step-1"))

    assert result == {
        "type": "replay_one_result",
        "ok": False,
        "step_id": "step-1",
        "failed_operation_id": "op_1",
        "error": "assertion failed",
    }
    assert executed_actions == ["assert"]


def test_replay_one_returns_unsupported_action_failure_without_crashing() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    hover_record = _make_hover_record(step_context)
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-1": {
            "step_id": "step-1",
            "children": [
                {"operation_id": "op_1", "type": "hover"},
            ],
        }
    }
    loop.replay_action_history_by_step_id = {"step-1": [hover_record]}

    result = asyncio.run(loop.replay_one("step-1"))

    assert result == {
        "type": "replay_one_result",
        "ok": False,
        "step_id": "step-1",
        "failed_operation_id": "op_1",
        "error": "Unsupported replay operation: hover",
    }


def test_replay_one_uses_archive_state_after_live_cleanup() -> None:
    loop = _make_loop()
    step_context = _make_step_context()
    assert_record = _make_assert_record(step_context)
    click_record = _make_click_record(step_context)
    recorded_payload = {
        "step_id": "step-1",
        "step_number": 1,
        "intent": step_context["intent"],
        "action": "click",
        "element_name": "Get started",
        "locator": 'get_by_label("Get started")',
        "generated_line": "await getStarted.click();",
        "status": "success",
        "children": [
            {
                "operation_id": "op_1",
                "type": "assert",
                "description": "Get started is visible",
                "target": "Get started",
                "locator": 'get_by_label("Get started")',
                "status": "success",
                "code_lines": ["await expect(getStarted).toBeVisible();"],
            },
            {
                "operation_id": "op_2",
                "type": "click",
                "description": "Get started",
                "target": "Get started",
                "locator": 'get_by_label("Get started")',
                "status": "success",
                "code_lines": ["await getStarted.click();"],
            },
        ],
    }
    loop.replay_recorded_step_payloads_by_step_id = {"step-1": recorded_payload}
    loop.replay_action_history_by_step_id = {"step-1": [assert_record, click_record]}
    loop.recorded_step_payloads = []
    loop.code_update_payloads = []

    executed_actions: list[str] = []

    async def fake_assert(args: dict[str, object]) -> dict[str, object]:
        executed_actions.append("assert")
        return {"success": True, "error": None}

    async def fake_click(args: dict[str, object]) -> dict[str, object]:
        executed_actions.append("click")
        return {"success": True, "error": None}

    loop._tool_action_assert = fake_assert
    loop._tool_action_click = fake_click

    result = asyncio.run(loop.replay_one("step-1"))

    assert result["ok"] is True
    assert result["operation_count"] == 2
    assert executed_actions == ["assert", "click"]
    assert loop.recorded_step_payloads == []
    assert loop.code_update_payloads == []
    assert loop.phase == "planning"
    assert loop.plan_confirmed is True
    assert loop.pending_recovery is False
    assert loop.current_steps == []
    assert loop.completed_step_ids == set()
    assert loop.skipped_step_ids == set()
    assert loop.phase_tracker.current_phase == "idle"


def _install_server_stubs(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    fake_queue = FakeQueue()
    created: dict[str, object] = {}

    async def fake_launch_browser() -> None:
        return None

    class FakeAgentLoop:
        def __init__(self, ws, control_queue) -> None:
            self.ws = ws
            self.control_queue = control_queue
            self.step_ids: list[str] = []
            created["agent"] = self

        async def run(self, steps) -> None:  # noqa: ARG002
            return None

        async def replay_one(self, step_id: str) -> dict[str, object]:
            self.step_ids.append(step_id)
            return {
                "type": "replay_one_result",
                "ok": True,
                "step_id": step_id,
                "status": "success",
                "operation_count": 2,
            }

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    return fake_queue, created


def test_replay_one_websocket_route_does_not_use_control_queue(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            initial_message = websocket.receive_json()
            assert initial_message["type"] == "status"
            assert "Browser launched" in initial_message["message"]

            websocket.send_json({"type": "replay_one", "step_id": "step-1"})
            response = websocket.receive_json()

    assert response == {
        "type": "replay_one_result",
        "ok": True,
        "step_id": "step-1",
        "status": "success",
        "operation_count": 2,
    }
    assert created["agent"].step_ids == ["step-1"]
    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == []
