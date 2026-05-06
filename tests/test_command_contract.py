from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import server


class FakeQueue:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)


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
            self._replay_all_result_sent = False
            self.llm = SimpleNamespace(reset=lambda: None)
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


def test_replay_all_defaults_stop_on_error_true(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            initial_message = websocket.receive_json()
            assert initial_message["type"] == "status"
            websocket.send_json({"type": "replay_all"})
            response = websocket.receive_json()

    assert response["type"] == "replay_all_result"
    assert response["stop_on_error"] is True
    assert created["agent"].stop_on_error_values == [True]
    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == []


@pytest.mark.xfail(strict=True, reason="supported commands are still forwarded raw instead of being typed-validated")
@pytest.mark.parametrize(
    ("command", "payload"),
    [
        ("confirmed", {"type": "confirmed", "command_id": "cmd-confirm"}),
        ("correction", {"type": "correction", "command_id": "cmd-correction"}),
        ("option_selected", {"type": "option_selected", "command_id": "cmd-option"}),
    ],
)
def test_supported_commands_require_context_before_being_forwarded(command, payload, monkeypatch) -> None:
    fake_queue, _created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json(payload)

    assert fake_queue.items == [], f"{command} should not be forwarded raw without validation"


@pytest.mark.xfail(strict=True, reason="unsupported commands still return generic errors instead of typed rejections")
@pytest.mark.parametrize(
    ("command", "payload"),
    [
        ("replay_step", {"type": "replay_step", "command_id": "cmd-replay-step", "step_id": "step-1"}),
        (
            "replay_operation",
            {
                "type": "replay_operation",
                "command_id": "cmd-replay-operation",
                "step_id": "step-1",
                "operation_id": "op_1",
            },
        ),
        ("skip_step", {"type": "skip_step", "command_id": "cmd-skip"}),
        ("stop_run", {"type": "stop_run", "command_id": "cmd-stop"}),
        ("save_session", {"type": "save_session", "command_id": "cmd-save"}),
        ("load_session", {"type": "load_session", "command_id": "cmd-load"}),
        (
            "update_locator",
            {
                "type": "update_locator",
                "command_id": "cmd-update",
                "step_id": "step-1",
                "operation_id": "op_1",
            },
        ),
        ("unknown_command", {"type": "unknown_command", "command_id": "cmd-unknown"}),
    ],
)
def test_unsupported_commands_return_typed_runtime_rejected(command, payload, monkeypatch) -> None:
    fake_queue, _created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json(payload)
            response = websocket.receive_json()

    assert response["type"] == "runtime_rejected"
    assert response["command_id"] == payload["command_id"], f"{command} should keep its command_id in the typed rejection"
    assert response["message"]
    assert fake_queue.items == []
