from __future__ import annotations

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import agent as agent_module
import server
from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


class FakeQueue:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)


class FakePage:
    def __init__(self, url: str, title: str) -> None:
        self.url = url
        self.title_value = title
        self.goto_calls: list[tuple[str, str]] = []

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        self.goto_calls.append((url, wait_until))
        self.url = url
        if "docs" in url:
            self.title_value = "Installation | Playwright"
        else:
            self.title_value = "Playwright"

    async def title(self) -> str:
        return self.title_value


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


def _make_recorded_payload(
    step_id: str,
    step_number: int,
    *,
    before_url: str | None = None,
    before_title: str | None = None,
    locator: str | None = None,
    child_locator: str | None = None,
) -> dict[str, object]:
    step_locator = f"#step-{step_number}" if locator is None else locator
    child_step_locator = step_locator if child_locator is None else child_locator
    payload: dict[str, object] = {
        "step_id": step_id,
        "step_number": step_number,
        "intent": f"Intent {step_number}",
        "action": "click",
        "element_name": f"Step {step_number}",
        "locator": step_locator,
        "generated_line": f"await step{step_number}.click();",
        "status": "success",
        "children": [
            {
                "operation_id": "op_1",
                "type": "click",
                "description": f"Step {step_number}",
                "target": f"Step {step_number}",
                "locator": child_step_locator,
                "status": "success",
                "code_lines": [f"await step{step_number}.click();"],
            }
        ],
    }
    if before_url is not None or before_title is not None:
        observed_outcome: dict[str, object] = {}
        if before_url is not None:
            observed_outcome["before_url"] = before_url
        if before_title is not None:
            observed_outcome["before_title"] = before_title
        payload["observed_outcome"] = observed_outcome
    return payload


def _make_success_result(step_id: str) -> dict[str, object]:
    return {
        "type": "replay_one_result",
        "ok": True,
        "step_id": step_id,
        "status": "success",
        "operation_count": 1,
    }


def _make_failure_result(step_id: str, failed_operation_id: str, error: str) -> dict[str, object]:
    return {
        "type": "replay_one_result",
        "ok": False,
        "step_id": step_id,
        "failed_operation_id": failed_operation_id,
        "error": error,
    }


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
            self.stop_on_error_values: list[bool] = []
            created["agent"] = self

        async def run(self, steps) -> None:  # noqa: ARG002
            return None

        async def replay_all(self, stop_on_error: bool = True) -> dict[str, object]:
            self.stop_on_error_values.append(stop_on_error)
            result = {
                "type": "replay_all_result",
                "ok": True,
                "stop_on_error": stop_on_error,
                "step_ids": ["step-1"],
                "replayed_count": 1,
                "passed_count": 1,
                "failed_count": 0,
            }
            self._replay_all_result_sent = True
            await self.ws.send_json(result)
            return result

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    return fake_queue, created


def test_replay_all_uses_backend_archive_order_and_calls_replay_one_for_each_step() -> None:
    loop = _make_loop()
    loop.recorded_step_payloads = [
        _make_recorded_payload("step-2", 2),
        _make_recorded_payload("step-1", 1),
        _make_recorded_payload("step-3", 3),
    ]
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-2": loop.recorded_step_payloads[0],
        "step-1": loop.recorded_step_payloads[1],
        "step-3": loop.recorded_step_payloads[2],
    }

    messages: list[dict[str, object]] = []
    calls: list[str] = []

    async def fake_send(msg_type: str, **kwargs: object) -> None:
        messages.append({"type": msg_type, **kwargs})

    async def fake_replay_one(step_id: str) -> dict[str, object]:
        calls.append(step_id)
        return _make_success_result(step_id)

    loop._send = fake_send
    loop.replay_one = fake_replay_one

    result = asyncio.run(loop.replay_all())

    assert calls == ["step-2", "step-1", "step-3"]
    assert messages == [
        {"type": "replay_started", "scope": "all", "step_count": 3},
        {"type": "replay_result", "step_id": "step-2", "ok": True, "status": "success", "operation_count": 1},
        {"type": "replay_result", "step_id": "step-1", "ok": True, "status": "success", "operation_count": 1},
        {"type": "replay_result", "step_id": "step-3", "ok": True, "status": "success", "operation_count": 1},
        {
            "type": "replay_all_result",
            "ok": True,
            "stop_on_error": True,
            "step_ids": ["step-2", "step-1", "step-3"],
            "replayed_count": 3,
            "passed_count": 3,
            "failed_count": 0,
        },
    ]
    assert result == {
        "type": "replay_all_result",
        "ok": True,
        "stop_on_error": True,
        "step_ids": ["step-2", "step-1", "step-3"],
        "replayed_count": 3,
        "passed_count": 3,
        "failed_count": 0,
    }


def test_replay_all_stops_sending_after_websocket_disconnect(
    capsys: pytest.CaptureFixture[str],
) -> None:
    loop = _make_loop()
    loop.recorded_step_payloads = [
        _make_recorded_payload("step-1", 1),
        _make_recorded_payload("step-2", 2),
    ]
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-1": loop.recorded_step_payloads[0],
        "step-2": loop.recorded_step_payloads[1],
    }

    class DisconnectingWebSocket:
        def __init__(self) -> None:
            self.payloads: list[dict[str, object]] = []

        async def send_json(self, payload: dict[str, object]) -> None:
            self.payloads.append(payload)
            if len(self.payloads) == 2:
                raise RuntimeError('Cannot call "send" once a close message has been sent.')

    fake_ws = DisconnectingWebSocket()
    loop.ws = fake_ws

    calls: list[str] = []

    async def fake_replay_one(step_id: str) -> dict[str, object]:
        calls.append(step_id)
        return _make_success_result(step_id)

    loop.replay_one = fake_replay_one

    result = asyncio.run(loop.replay_all())
    captured = capsys.readouterr().out

    assert calls == ["step-1", "step-2"]
    assert fake_ws.payloads == [
        {"type": "replay_started", "scope": "all", "step_count": 2},
        {"type": "replay_result", "step_id": "step-1", "ok": True, "status": "success", "operation_count": 1},
    ]
    assert result == {
        "type": "replay_all_result",
        "ok": True,
        "stop_on_error": True,
        "step_ids": ["step-1", "step-2"],
        "replayed_count": 2,
        "passed_count": 2,
        "failed_count": 0,
    }
    assert getattr(loop, "_ws_disconnected", False) is True
    assert "[WS] disconnected during replay_all; stopping result send" in captured


def test_replay_all_emits_compact_backend_logs(capsys: pytest.CaptureFixture[str]) -> None:
    loop = _make_loop()
    loop.recorded_step_payloads = [
        _make_recorded_payload("step-1", 1),
        _make_recorded_payload("step-2", 2),
    ]
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-1": loop.recorded_step_payloads[0],
        "step-2": loop.recorded_step_payloads[1],
    }

    async def fake_send(msg_type: str, **kwargs: object) -> None:  # noqa: ARG001
        return None

    async def fake_replay_one(step_id: str) -> dict[str, object]:
        return _make_success_result(step_id)

    loop._send = fake_send
    loop.replay_one = fake_replay_one

    result = asyncio.run(loop.replay_all())
    captured = capsys.readouterr().out

    assert result == {
        "type": "replay_all_result",
        "ok": True,
        "stop_on_error": True,
        "step_ids": ["step-1", "step-2"],
        "replayed_count": 2,
        "passed_count": 2,
        "failed_count": 0,
    }
    assert "[REPLAY_ALL] started steps=2 stop_on_error=true" in captured
    assert "[REPLAY_ALL] step_result step_id=step-1 ok=true operations=1" in captured
    assert "[REPLAY_ALL] step_result step_id=step-2 ok=true operations=1" in captured
    assert "[REPLAY_ALL] completed total=2 passed=2 failed=0" in captured


def test_replay_all_uses_auto_recorded_archive_order(monkeypatch) -> None:
    loop = _make_loop()
    step_one_context = {
        "step_id": "step-1",
        "step_number": 1,
        "intent": "Click the first button",
        "element_info": {
            "text": "First",
            "attributes": {"aria-label": "First"},
        },
        "element_name": "First",
        "locator": None,
        "status": "executing",
        "recorded": False,
        "last_error": None,
        "expected_outcome": {
            "type": "navigation",
            "description": "goes to the first page",
            "source": "user",
            "required": True,
        },
    }
    step_two_context = {
        "step_id": "step-2",
        "step_number": 2,
        "intent": "Click the second button",
        "element_info": {
            "text": "Second",
            "attributes": {"aria-label": "Second"},
        },
        "element_name": "Second",
        "locator": None,
        "status": "executing",
        "recorded": False,
        "last_error": None,
        "expected_outcome": {
            "type": "navigation",
            "description": "goes to the second page",
            "source": "user",
            "required": True,
        },
    }
    step_one_record = {
        "tool": "action_click",
        "action": "click",
        "locator": 'get_by_label("First")',
        "result": {"success": True, "skipped": False},
        "step_context": step_one_context,
        "action_context": {"locator": 'get_by_label("First")'},
        "tool_args": {"locator": 'get_by_label("First")'},
        "step_id": "step-1",
        "step_number": 1,
    }
    step_two_record = {
        "tool": "action_click",
        "action": "click",
        "locator": 'get_by_label("Second")',
        "result": {"success": True, "skipped": False},
        "step_context": step_two_context,
        "action_context": {"locator": 'get_by_label("Second")'},
        "tool_args": {"locator": 'get_by_label("Second")'},
        "step_id": "step-2",
        "step_number": 2,
    }

    loop._recording_steps = [step_one_context, step_two_context]
    loop.step_state_by_id = {"step-1": step_one_context, "step-2": step_two_context}
    loop.step_context_by_id = loop.step_state_by_id
    loop.plan_confirmed = True
    loop.active_step_id = "step-1"
    loop.last_successful_action = step_one_record
    loop.successful_action_by_step_id = {"step-1": step_one_record}
    loop.successful_actions_by_step_id = {"step-1": [step_one_record]}
    loop.replay_action_history_by_step_id = {"step-1": [step_one_record]}

    sent_messages: list[dict[str, object]] = []

    async def fake_send(msg_type: str, **kwargs: object) -> None:
        sent_messages.append({"type": msg_type, **kwargs})

    loop._send = fake_send
    asyncio.run(loop._auto_record_successful_step())

    loop.active_step_id = "step-2"
    loop.last_successful_action = step_two_record
    loop.successful_action_by_step_id = {"step-2": step_two_record}
    loop.successful_actions_by_step_id = {"step-2": [step_two_record]}
    loop.replay_action_history_by_step_id["step-2"] = [step_two_record]
    asyncio.run(loop._auto_record_successful_step())

    fake_page = FakePage("https://playwright.dev/", "Playwright")
    monkeypatch.setattr(agent_module, "get_page", lambda: fake_page)

    calls: list[str] = []

    async def fake_replay_one(step_id: str) -> dict[str, object]:
        calls.append(step_id)
        return _make_success_result(step_id)

    loop.replay_one = fake_replay_one

    result = asyncio.run(loop.replay_all())

    assert sent_messages[0]["type"] == "step_recorded"
    assert sent_messages[2]["type"] == "step_recorded"
    assert calls == ["step-1", "step-2"]
    assert result == {
        "type": "replay_all_result",
        "ok": True,
        "stop_on_error": True,
        "step_ids": ["step-1", "step-2"],
        "replayed_count": 2,
        "passed_count": 2,
        "failed_count": 0,
    }


def test_replay_all_restores_first_before_url_before_replaying(
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    loop = _make_loop()
    loop.recorded_step_payloads = [
        _make_recorded_payload(
            "step-1",
            1,
            before_url="https://playwright.dev/",
            before_title="Playwright",
            locator='get_by_label("First")',
            child_locator='get_by_label("First")',
        ),
        _make_recorded_payload("step-2", 2),
    ]
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-1": loop.recorded_step_payloads[0],
        "step-2": loop.recorded_step_payloads[1],
    }
    loop.replay_action_history_by_step_id = {
        "step-1": [
            {
                "tool": "action_click",
                "action": "click",
                "locator": 'get_by_label("First")',
                "result": {"success": True, "skipped": False},
                "action_context": {"locator": 'get_by_label("First")'},
                "tool_args": {"locator": 'get_by_label("First")'},
                "step_id": "step-1",
                "step_number": 1,
            }
        ],
        "step-2": [
            {
                "tool": "action_click",
                "action": "click",
                "locator": "",
                "result": {"success": True, "skipped": False},
                "action_context": {},
                "tool_args": {},
                "step_id": "step-2",
                "step_number": 2,
            }
        ],
    }

    fake_page = FakePage("https://playwright.dev/docs/intro", "Installation | Playwright")
    monkeypatch.setattr(agent_module, "get_page", lambda: fake_page)

    calls: list[str] = []

    async def fake_send(msg_type: str, **kwargs: object) -> None:  # noqa: ARG001
        return None

    async def fake_replay_one(step_id: str) -> dict[str, object]:
        calls.append(step_id)
        return _make_success_result(step_id)

    loop._send = fake_send
    loop.replay_one = fake_replay_one

    result = asyncio.run(loop.replay_all())
    captured = capsys.readouterr().out

    assert fake_page.goto_calls == [("https://playwright.dev/", "domcontentloaded")]
    assert "[REPLAY_ALL] restoring_start_url url=https://playwright.dev/" in captured
    assert calls == ["step-1", "step-2"]
    assert result == {
        "type": "replay_all_result",
        "ok": True,
        "stop_on_error": True,
        "step_ids": ["step-1", "step-2"],
        "replayed_count": 2,
        "passed_count": 2,
        "failed_count": 0,
    }


def test_replay_all_server_helper_skips_closed_socket_without_fallback_send(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class ForbiddenWebSocket:
        def __init__(self) -> None:
            self.send_calls = 0

        async def send_json(self, payload: dict[str, object]) -> None:  # noqa: ARG002
            self.send_calls += 1
            raise AssertionError("send_json should not be called")

    fake_ws = ForbiddenWebSocket()
    fake_agent = SimpleNamespace(_ws_disconnected=True, _ws_disconnect_logged=False)

    result = asyncio.run(
        server._send_replay_json(
            fake_ws,
            fake_agent,
            {
                "type": "replay_all_result",
                "ok": False,
            },
        )
    )
    captured = capsys.readouterr().out

    assert result is False
    assert fake_ws.send_calls == 0
    assert fake_agent._ws_disconnected is True
    assert fake_agent._ws_disconnect_logged is True
    assert "[WS] disconnected during replay_all; stopping result send" in captured


def test_replay_all_stops_on_precondition_failure(
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    loop = _make_loop()
    loop.recorded_step_payloads = [
        _make_recorded_payload(
            "step-1",
            1,
            before_url="https://playwright.dev/",
            before_title="Playwright",
            locator='get_by_label("First")',
            child_locator='get_by_label("First")',
        ),
        _make_recorded_payload(
            "step-2",
            2,
            before_url="https://playwright.dev/",
            before_title="Playwright",
            locator="",
            child_locator="",
        ),
    ]
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-1": loop.recorded_step_payloads[0],
        "step-2": loop.recorded_step_payloads[1],
    }
    loop.replay_action_history_by_step_id = {
        "step-1": [
            {
                "tool": "action_click",
                "action": "click",
                "locator": 'get_by_label("First")',
                "result": {"success": True, "skipped": False},
                "action_context": {"locator": 'get_by_label("First")'},
                "tool_args": {"locator": 'get_by_label("First")'},
                "step_id": "step-1",
                "step_number": 1,
            }
        ],
        "step-2": [
            {
                "tool": "action_click",
                "action": "click",
                "locator": 'get_by_label("Second")',
                "result": {"success": True, "skipped": False},
                "action_context": {"locator": 'get_by_label("Second")'},
                "tool_args": {"locator": 'get_by_label("Second")'},
                "step_id": "step-2",
                "step_number": 2,
            }
        ],
    }

    fake_page = FakePage("https://playwright.dev/docs/intro", "Installation | Playwright")
    monkeypatch.setattr(agent_module, "get_page", lambda: fake_page)

    executed_actions: list[str] = []
    validate_calls: list[str] = []
    messages: list[dict[str, object]] = []

    async def fake_capture_browser_state() -> dict[str, str]:
        return {
            "url": fake_page.url,
            "title": fake_page.title_value,
        }

    async def fake_validate_target_locator(locator: str) -> dict[str, object]:
        validate_calls.append(locator)
        if locator == 'get_by_label("Second")':
            return {"valid": False, "count": 0}
        return {"valid": True, "count": 1}

    async def fake_click(args: dict[str, object]) -> dict[str, object]:
        executed_actions.append(str(args.get("locator") or ""))
        return {"success": True, "error": None}

    async def fake_send(msg_type: str, **kwargs: object) -> None:
        messages.append({"type": msg_type, **kwargs})

    loop._capture_browser_state = fake_capture_browser_state
    loop._validate_replay_target_locator = fake_validate_target_locator
    loop._tool_action_click = fake_click
    loop._send = fake_send

    result = asyncio.run(loop.replay_all())
    captured = capsys.readouterr().out

    assert fake_page.goto_calls == [("https://playwright.dev/", "domcontentloaded")]
    assert executed_actions == ['get_by_label("First")']
    assert validate_calls == ['get_by_label("First")', 'get_by_label("Second")']
    assert (
        "[REPLAY_PRECONDITION] failed step_id=step-2 reason=locator_missing "
        'locator=get_by_label("Second")'
    ) in captured
    assert messages == [
        {"type": "replay_started", "scope": "all", "step_count": 2},
        {
            "type": "replay_result",
            "step_id": "step-1",
            "ok": True,
            "status": "success",
            "operation_count": 1,
        },
        {
            "type": "replay_result",
            "step_id": "step-2",
            "ok": False,
            "status": "failed",
            "operation_count": 0,
            "reason": "replay_precondition_failed",
            "failure_type": "locator_missing",
            "expected": {
                "before_url": "https://playwright.dev/",
                "before_title": "Playwright",
            },
            "actual": {
                "url": "https://playwright.dev/",
                "title": "Playwright",
            },
            "message": "Element not found",
            "error": "Element not found",
        },
        {
            "type": "replay_all_result",
            "ok": False,
            "stop_on_error": True,
            "step_ids": ["step-1", "step-2"],
            "replayed_count": 2,
            "passed_count": 1,
            "failed_count": 1,
            "failed_step_id": "step-2",
            "error": "Element not found",
        },
    ]
    assert result == {
        "type": "replay_all_result",
        "ok": False,
        "stop_on_error": True,
        "step_ids": ["step-1", "step-2"],
        "replayed_count": 2,
        "passed_count": 1,
        "failed_count": 1,
        "failed_step_id": "step-2",
        "error": "Element not found",
    }


def test_replay_all_stops_on_first_failed_step_and_reports_counts() -> None:
    loop = _make_loop()
    loop.recorded_step_payloads = [
        _make_recorded_payload("step-1", 1),
        _make_recorded_payload("step-2", 2),
        _make_recorded_payload("step-3", 3),
    ]
    loop.replay_recorded_step_payloads_by_step_id = {
        "step-1": loop.recorded_step_payloads[0],
        "step-2": loop.recorded_step_payloads[1],
        "step-3": loop.recorded_step_payloads[2],
    }

    messages: list[dict[str, object]] = []
    calls: list[str] = []

    async def fake_send(msg_type: str, **kwargs: object) -> None:
        messages.append({"type": msg_type, **kwargs})

    async def fake_replay_one(step_id: str) -> dict[str, object]:
        calls.append(step_id)
        if step_id == "step-2":
            return _make_failure_result(step_id, "op_2", "boom")
        return _make_success_result(step_id)

    loop._send = fake_send
    loop.replay_one = fake_replay_one

    result = asyncio.run(loop.replay_all())

    assert calls == ["step-1", "step-2"]
    assert messages == [
        {"type": "replay_started", "scope": "all", "step_count": 3},
        {"type": "replay_result", "step_id": "step-1", "ok": True, "status": "success", "operation_count": 1},
        {
            "type": "replay_result",
            "step_id": "step-2",
            "ok": False,
            "status": "failed",
            "operation_count": 0,
            "failed_operation_id": "op_2",
            "error": "boom",
        },
        {
            "type": "replay_all_result",
            "ok": False,
            "stop_on_error": True,
            "step_ids": ["step-1", "step-2", "step-3"],
            "replayed_count": 2,
            "passed_count": 1,
            "failed_count": 1,
            "failed_step_id": "step-2",
            "failed_operation_id": "op_2",
            "error": "boom",
        },
    ]
    assert result == {
        "type": "replay_all_result",
        "ok": False,
        "stop_on_error": True,
        "step_ids": ["step-1", "step-2", "step-3"],
        "replayed_count": 2,
        "passed_count": 1,
        "failed_count": 1,
        "failed_step_id": "step-2",
        "failed_operation_id": "op_2",
        "error": "boom",
    }


def test_replay_all_websocket_route_does_not_use_control_queue(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            initial_message = websocket.receive_json()
            assert initial_message["type"] in {"status", "ready"}

            websocket.send_json({"type": "replay_all", "stop_on_error": False})
            response = websocket.receive_json()

    assert response == {
        "type": "replay_all_result",
        "ok": True,
        "stop_on_error": False,
        "step_ids": ["step-1"],
        "replayed_count": 1,
        "passed_count": 1,
        "failed_count": 0,
    }
    assert created["agent"].stop_on_error_values == [False]
    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == []


def test_replay_all_does_not_mutate_recorded_payload_or_code_payload_state() -> None:
    loop = _make_loop()
    recorded_step_payloads = [_make_recorded_payload("step-1", 1)]
    code_update_payloads = [{"step_id": "step-1", "lines": ["await step1.click();"]}]
    replay_recorded_step_payloads_by_step_id = {"step-1": deepcopy(recorded_step_payloads[0])}
    replay_action_history_by_step_id = {
        "step-1": [
            {
                "tool": "action_click",
                "action": "click",
                "locator": "#step-1",
                "result": {"success": True, "skipped": False},
                "action_context": {"locator": "#step-1"},
                "tool_args": {"locator": "#step-1"},
                "step_id": "step-1",
                "step_number": 1,
            }
        ]
    }
    original_recorded_step_payloads = deepcopy(recorded_step_payloads)
    original_code_update_payloads = deepcopy(code_update_payloads)
    original_replay_recorded_step_payloads_by_step_id = deepcopy(replay_recorded_step_payloads_by_step_id)
    original_replay_action_history_by_step_id = deepcopy(replay_action_history_by_step_id)

    loop.recorded_step_payloads = recorded_step_payloads
    loop.code_update_payloads = code_update_payloads
    loop.replay_recorded_step_payloads_by_step_id = replay_recorded_step_payloads_by_step_id
    loop.replay_action_history_by_step_id = replay_action_history_by_step_id
    loop.phase = "planning"
    loop.plan_confirmed = True
    loop.pending_recovery = False
    loop.completed_step_ids = set()
    loop.skipped_step_ids = set()

    async def fake_send(msg_type: str, **kwargs: object) -> None:  # noqa: ARG001
        return None

    async def fake_replay_one(step_id: str) -> dict[str, object]:
        return _make_success_result(step_id)

    loop._send = fake_send
    loop.replay_one = fake_replay_one

    result = asyncio.run(loop.replay_all())

    assert result["ok"] is True
    assert loop.recorded_step_payloads == original_recorded_step_payloads
    assert loop.code_update_payloads == original_code_update_payloads
    assert loop.replay_recorded_step_payloads_by_step_id == original_replay_recorded_step_payloads_by_step_id
    assert loop.replay_action_history_by_step_id == original_replay_action_history_by_step_id
    assert loop.phase == "planning"
    assert loop.plan_confirmed is True
    assert loop.pending_recovery is False
    assert loop.completed_step_ids == set()
    assert loop.skipped_step_ids == set()
