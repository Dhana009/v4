from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server
from agent import AgentLoop
from runtime.event_contracts import FRONTEND_COMMAND_SCHEMA_VERSION, normalize_frontend_command
from runtime.phase_tracker import PhaseTracker


class QueueHarness:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []
        self.get_count = 0

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)

    async def get(self) -> dict[str, object]:
        self.get_count += 1
        if not self.items:
            raise AssertionError("expected another backend command")
        return self.items.pop(0)


def _install_server_stubs(
    monkeypatch,
    *,
    phase: str = "planning",
    run_id: str = "run-test-001",
) -> tuple[QueueHarness, dict[str, object]]:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setattr(server.app.state, "active_run_session", None, raising=False)

    fake_queue = QueueHarness()
    created: dict[str, object] = {}

    async def fake_launch_browser() -> None:
        return None

    class FakeAgentLoop:
        def __init__(self, ws, control_queue) -> None:
            self.ws = ws
            self.control_queue = control_queue
            self.phase = phase
            self._run_session_id = run_id
            self.llm = SimpleNamespace(reset=lambda: None)
            self.run_calls: list[list[dict[str, object]]] = []
            created["agent"] = self

        async def run(self, steps) -> None:
            self.run_calls.append(list(steps))
            return None

        def _current_phase(self) -> str:
            return self.phase

        def _current_run_session_id(self) -> str:
            return self._run_session_id

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    return fake_queue, created


def _make_confirmation_loop(
    queue: QueueHarness,
    *,
    phase: str,
    run_id: str,
    plan_id: str | None = None,
    completed: bool = False,
) -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.control_queue = queue
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = phase
    loop.phase = phase
    loop._run_session_id = run_id
    loop._run_completion_requested = False
    loop._run_completed_emitted = completed
    loop._recording_steps = []
    loop.last_plan_summary = "Run completed"
    loop.last_plan_ready_payload = None
    loop._active_plan_state = None
    if plan_id:
        loop._active_plan_state = {
            "run_id": run_id,
            "plan_id": plan_id,
            "plan_version": "v1",
            "summary": "Keep the active run state",
            "steps": [],
        }
    loop.pending_recovery = False
    loop.active_failed_step_id = None
    loop._pending_failure_followup = False
    loop.llm = SimpleNamespace(messages=[], system_prompt="", client=object(), reset=lambda: None)
    return loop


def test_websocket_malformed_command_returns_runtime_rejected_and_does_not_start_agent(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            initial_message = websocket.receive_json()
            assert initial_message["type"] in {"status", "ready"}

            websocket.send_json(
                {
                    "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
                    "command_id": "cmd-malformed",
                    "source": "frontend",
                    "payload": {"answer": "confirmed"},
                }
            )
            response = websocket.receive_json()

    assert response["type"] == "runtime_rejected"
    assert response["rejection_code"] == "MALFORMED_COMMAND"
    assert response["payload"]["rejection_code"] == "MALFORMED_COMMAND"
    assert fake_queue.items == []
    assert created["agent"].run_calls == []


def test_websocket_unknown_command_returns_runtime_rejected_and_does_not_start_agent(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json(
                {
                    "type": "unknown_command",
                    "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
                    "command_id": "cmd-unknown",
                    "source": "frontend",
                    "run_id": "run-test-001",
                    "payload": {},
                }
            )
            response = websocket.receive_json()

    assert response["type"] == "runtime_rejected"
    assert response["rejection_code"] == "COMMAND_NOT_SUPPORTED"
    assert response["command_id"] == "cmd-unknown"
    assert response["message"]
    assert fake_queue.items == []
    assert created["agent"].run_calls == []


def test_websocket_stale_run_id_command_is_rejected_without_queue_mutation(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch, phase="executing", run_id="run-current")

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json(
                {
                    "type": "confirmed",
                    "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
                    "command_id": "cmd-stale",
                    "source": "frontend",
                    "run_id": "run-old",
                    "plan_id": "plan-old",
                    "payload": {},
                }
            )
            response = websocket.receive_json()

    assert response["type"] == "runtime_rejected"
    assert response["rejection_code"] == "STALE_COMMAND"
    assert response["command_type"] == "confirmed"
    assert response["run_id"] == "run-old"
    assert response["current_state"]["run_id"] == "run-current"
    assert fake_queue.items == []
    assert created["agent"].run_calls == []


def test_completed_run_correction_from_websocket_is_rejected_by_backend_consumer(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch, phase="completed", run_id="run-completed")

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json(
                {
                    "type": "correction",
                    "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
                    "command_id": "cmd-late",
                    "source": "frontend",
                    "run_id": "run-completed",
                    "plan_id": "plan-completed",
                    "payload": {"message": "Use the newer plan"},
                }
            )

    assert fake_queue.items == [
        {
            "type": "correction",
            "message": "Use the newer plan",
            "run_id": "run-completed",
            "plan_id": "plan-completed",
        }
    ]
    assert created["agent"].run_calls == []

    loop = _make_confirmation_loop(
        fake_queue,
        phase="completed",
        run_id="run-completed",
        plan_id="plan-completed",
        completed=True,
    )
    sent_events: list[dict[str, object]] = []

    async def fake_send(message_type: str, **kwargs: object) -> None:
        sent_events.append({"type": message_type, **kwargs})

    loop._send = fake_send

    result = asyncio.run(loop._wait_for_plan_confirmation())

    assert len(sent_events) == 1
    rejection = sent_events[0]
    assert rejection["type"] == "runtime_rejected"
    assert rejection["rejection_code"] == "STALE_CONFIRMATION"
    assert rejection["run_id"] == "run-completed"
    assert rejection["payload"]["current_state"]["run_id"] == "run-completed"
    assert result["confirmed"] is False
    assert result["correction"] == "Use the newer plan"


def test_websocket_valid_canonical_command_preserves_command_correlation_before_queue_forward(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch, phase="planning", run_id="run-current")
    captured: dict[str, object] = {}
    real_normalize = normalize_frontend_command

    def spy_normalize(message_data, *, current_state=None):
        command, rejection = real_normalize(message_data, current_state=current_state)
        captured["command"] = command
        captured["rejection"] = rejection
        captured["current_state"] = dict(current_state or {})
        return command, rejection

    monkeypatch.setattr(server, "normalize_frontend_command", spy_normalize)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json(
                {
                    "type": "correction",
                    "schema_version": FRONTEND_COMMAND_SCHEMA_VERSION,
                    "command_id": "cmd-correlation",
                    "source": "frontend",
                    "run_id": "run-current",
                    "plan_id": "plan-current",
                    "payload": {"message": "Use the newer plan"},
                }
            )

    command = captured["command"]
    assert isinstance(command, dict)
    assert captured["rejection"] is None
    assert captured["current_state"] == {"phase": "planning", "run_id": "run-current"}
    assert command["type"] == "correction"
    assert command["schema_version"] == FRONTEND_COMMAND_SCHEMA_VERSION
    assert command["command_id"] == "cmd-correlation"
    assert command["run_id"] == "run-current"
    assert command["plan_id"] == "plan-current"
    assert command["payload"] == {
        "message": "Use the newer plan",
        "run_id": "run-current",
        "plan_id": "plan-current",
    }
    assert fake_queue.items == [
        {
            "type": "correction",
            "message": "Use the newer plan",
            "run_id": "run-current",
            "plan_id": "plan-current",
        }
    ]
    assert created["agent"].run_calls == []
