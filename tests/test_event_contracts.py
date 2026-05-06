from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import server
from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    FRONTEND_COMMAND_SCHEMA_VERSION,
    RUNTIME_REJECTION_SCHEMA_VERSION,
    build_backend_event_envelope,
    build_frontend_command_envelope,
    build_runtime_rejection_payload,
    normalize_frontend_command,
)


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
            self.llm = SimpleNamespace(reset=lambda: None)
            self._run_session_id = "run-test-001"
            created["agent"] = self

        def _current_phase(self) -> str:
            return "planning"

        def _current_run_session_id(self) -> str:
            return self._run_session_id

        async def run(self, steps) -> None:  # noqa: ARG002
            return None

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    return fake_queue, created


def test_backend_event_envelope_includes_canonical_metadata_and_legacy_fields() -> None:
    payload = {"message": "Browser launched. Ready."}

    envelope = build_backend_event_envelope(
        "status",
        payload,
        run_id="run-test-001",
        event_id="event-1",
        emitted_at="2026-05-05T00:00:00+00:00",
        source="server",
    )

    assert envelope["type"] == "status"
    assert envelope["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    assert envelope["run_id"] == "run-test-001"
    assert envelope["event_id"] == "event-1"
    assert envelope["emitted_at"] == "2026-05-05T00:00:00+00:00"
    assert envelope["source"] == "server"
    assert envelope["payload"] == payload
    assert envelope["message"] == "Browser launched. Ready."


def test_backend_event_envelope_requires_type() -> None:
    with pytest.raises(ValueError):
        build_backend_event_envelope("", {"message": "Browser launched. Ready."})


def test_frontend_command_envelope_includes_required_fields() -> None:
    envelope = build_frontend_command_envelope(
        "confirmed",
        {"answer": "confirmed"},
        command_id="cmd-1",
        source="frontend",
        run_id="run-test-001",
    )

    assert envelope["type"] == "confirmed"
    assert envelope["schema_version"] == FRONTEND_COMMAND_SCHEMA_VERSION
    assert envelope["command_id"] == "cmd-1"
    assert envelope["source"] == "frontend"
    assert envelope["run_id"] == "run-test-001"
    assert envelope["payload"] == {"answer": "confirmed"}


def test_frontend_command_envelope_requires_type() -> None:
    with pytest.raises(ValueError):
        build_frontend_command_envelope("", {"answer": "confirmed"}, command_id="cmd-1", source="frontend")


def test_runtime_rejection_payload_includes_required_details() -> None:
    rejection = build_runtime_rejection_payload(
        "MALFORMED_COMMAND",
        "Missing command_id",
        current_state={"phase": "planning"},
        command_id="cmd-1",
        run_id="run-test-001",
        recoverable=False,
    )

    assert rejection["type"] == "runtime_rejected"
    assert rejection["schema_version"] == RUNTIME_REJECTION_SCHEMA_VERSION
    assert rejection["rejection_code"] == "MALFORMED_COMMAND"
    assert rejection["message"] == "Missing command_id"
    assert rejection["current_state"] == {"phase": "planning"}
    assert rejection["command_id"] == "cmd-1"
    assert rejection["run_id"] == "run-test-001"
    assert rejection["recoverable"] is False


def test_legacy_frontend_command_is_normalized_safely() -> None:
    command, rejection = normalize_frontend_command({"type": "confirmed"})

    assert rejection is None
    assert command is not None
    assert command["type"] == "confirmed"
    assert command["schema_version"] == FRONTEND_COMMAND_SCHEMA_VERSION
    assert command["source"] == "legacy"
    assert command["command_id"]
    assert command["payload"] == {}


def test_canonical_frontend_command_missing_command_id_returns_runtime_rejected() -> None:
    command, rejection = normalize_frontend_command(
        {
            "type": "confirmed",
            "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
            "source": "frontend",
            "payload": {"answer": "confirmed"},
        },
        current_state={"phase": "planning"},
    )

    assert command is None
    assert rejection is not None
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "MALFORMED_COMMAND"
    assert rejection["current_state"] == {"phase": "planning"}


def test_websocket_accepts_canonical_confirmation_command_envelope(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            initial_message = websocket.receive_json()
            assert initial_message["type"] == "status"
            assert "Browser launched" in initial_message["message"]

            websocket.send_json(
                {
                    "type": "confirmed",
                    "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
                    "command_id": "cmd-1",
                    "source": "frontend",
                    "payload": {},
                }
            )

    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == [{"type": "confirmed"}]


def test_websocket_accepts_legacy_confirmation_command_for_compatibility(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "confirmed"})

    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == [{"type": "confirmed"}]


def test_websocket_rejects_malformed_canonical_command_with_typed_rejection(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            initial_message = websocket.receive_json()
            assert initial_message["type"] == "status"

            websocket.send_json(
                {
                    "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
                    "command_id": "cmd-2",
                    "source": "frontend",
                    "payload": {"answer": "confirmed"},
                }
            )
            response = websocket.receive_json()

    assert response["type"] == "runtime_rejected"
    assert response["schema_version"] == RUNTIME_REJECTION_SCHEMA_VERSION
    assert response["payload"]["type"] == "runtime_rejected"
    assert response["payload"]["rejection_code"] == "MALFORMED_COMMAND"
    assert response["payload"]["current_state"] == {"phase": "planning", "run_id": "run-test-001"}
    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == []
