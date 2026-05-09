"""WSRouter gap-coverage tests.

Covers WSRouter routes that were not tested by any existing file:
  - run_steps  → agent.run() is called with the forwarded steps
  - run_steps  → "already in progress" guard when a run task is active
  - reset      → agent.llm.reset() is called and a status message is returned
  - arm_picker → missing step_id returns a typed error without touching the queue

All tests use FastAPI TestClient + fake AgentLoop with no live browser or LLM.
"""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server


# ---------------------------------------------------------------------------
# Shared harness helpers
# ---------------------------------------------------------------------------

class _SimpleQueue:
    """Minimal async-compatible queue without a get() path (put-only spy)."""

    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)


def _install_stubs(monkeypatch, *, agent_cls=None) -> tuple[_SimpleQueue, dict[str, object]]:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setattr(server.app.state, "active_run_session", None, raising=False)

    fake_queue = _SimpleQueue()
    created: dict[str, object] = {}

    async def fake_launch_browser() -> None:
        return None

    if agent_cls is None:
        class _DefaultAgent:
            def __init__(self, ws, control_queue) -> None:
                self.ws = ws
                self.control_queue = control_queue
                self.llm = SimpleNamespace(reset=lambda: None)
                self.run_calls: list[list] = []
                created["agent"] = self

            async def run(self, steps) -> None:
                self.run_calls.append(list(steps))

        agent_cls = _DefaultAgent

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", agent_cls)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    return fake_queue, created


# ---------------------------------------------------------------------------
# run_steps → agent.run()
# ---------------------------------------------------------------------------

def test_run_steps_routes_to_agent_run_with_forwarded_steps(monkeypatch) -> None:
    """run_steps command must call agent.run() exactly once with the supplied steps."""
    fake_queue, created = _install_stubs(monkeypatch)

    steps = [{"id": "step-1", "intent": "click the submit button"}]

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # initial "Browser launched" status
            websocket.send_json({"type": "run_steps", "steps": steps})

    assert created["agent"].run_calls == [steps]
    # run_steps must NOT enqueue anything on the control queue
    assert fake_queue.items == []


def test_llm_run_routes_to_agent_run_with_forwarded_steps(monkeypatch) -> None:
    """llm_run is an alias for run_steps and must also call agent.run()."""
    fake_queue, created = _install_stubs(monkeypatch)

    steps = [{"id": "step-1", "intent": "assert visible the heading"}]

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "llm_run", "steps": steps})

    assert created["agent"].run_calls == [steps]
    assert fake_queue.items == []


def test_run_steps_with_empty_steps_list_still_calls_agent_run(monkeypatch) -> None:
    """run_steps with an empty steps list must still call agent.run([])."""
    fake_queue, created = _install_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "run_steps", "steps": []})

    assert created["agent"].run_calls == [[]]
    assert fake_queue.items == []


def test_run_steps_with_missing_steps_key_defaults_to_empty_list(monkeypatch) -> None:
    """run_steps with no 'steps' key must call agent.run([]) (not crash)."""
    fake_queue, created = _install_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "run_steps"})  # no 'steps' key

    assert created["agent"].run_calls == [[]]
    assert fake_queue.items == []


# ---------------------------------------------------------------------------
# run_steps → already-in-progress guard
# ---------------------------------------------------------------------------

def test_run_steps_while_run_already_active_returns_status_and_does_not_start_second_run(
    monkeypatch,
) -> None:
    """If a run task is still active, a second run_steps must return a status
    message and must NOT call agent.run() a second time."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setattr(server.app.state, "active_run_session", None, raising=False)

    fake_queue = _SimpleQueue()
    run_calls: list[int] = []
    run_started = threading.Event()
    block_run = threading.Event()

    class _BlockingAgent:
        def __init__(self, ws, control_queue) -> None:
            self.ws = ws
            self.control_queue = control_queue
            self.llm = SimpleNamespace(reset=lambda: None)

        async def run(self, steps) -> None:  # noqa: ARG002
            run_calls.append(1)
            run_started.set()
            # Block until the test releases us so the task stays "active"
            await asyncio.to_thread(block_run.wait, 3.0)

    async def fake_launch_browser() -> None:
        return None

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", _BlockingAgent)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # initial status

            # First run_steps — starts a background task
            websocket.send_json({"type": "run_steps", "steps": [{"id": "step-1"}]})
            assert run_started.wait(timeout=2.0), "first run did not start"

            # Second run_steps while first is still blocking
            websocket.send_json({"type": "run_steps", "steps": [{"id": "step-2"}]})
            response = websocket.receive_json()

            block_run.set()  # release the first run so the test can finish

    assert response["type"] == "status"
    assert "in progress" in response["message"].lower()
    # agent.run() must have been invoked only once (the first command)
    assert run_calls == [1]
    assert fake_queue.items == []


# ---------------------------------------------------------------------------
# reset command
# ---------------------------------------------------------------------------

def test_reset_calls_llm_reset_and_returns_status_message(monkeypatch) -> None:
    """reset command must call agent.llm.reset() and return a status message."""
    fake_queue, created = _install_stubs(monkeypatch)
    reset_calls: list[int] = []

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # initial status

            # Patch reset on the already-instantiated agent
            created["agent"].llm.reset = lambda: reset_calls.append(1)

            websocket.send_json({"type": "reset"})
            response = websocket.receive_json()

    assert response["type"] == "status"
    assert "reset" in response["message"].lower()
    assert reset_calls == [1]
    # reset must not touch the control queue
    assert fake_queue.items == []


def test_reset_does_not_start_a_run(monkeypatch) -> None:
    """reset must never call agent.run()."""
    fake_queue, created = _install_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "reset"})
            websocket.receive_json()  # consume status

    assert created["agent"].run_calls == []
    assert fake_queue.items == []


# ---------------------------------------------------------------------------
# arm_picker command
# ---------------------------------------------------------------------------

def test_arm_picker_missing_step_id_returns_error_without_queue_mutation(monkeypatch) -> None:
    """arm_picker without step_id must return a typed error and must not
    enqueue anything on the control queue or call agent.run()."""
    fake_queue, created = _install_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "arm_picker"})  # no step_id
            response = websocket.receive_json()

    assert response["type"] == "error"
    assert "step_id" in response["message"].lower()
    assert fake_queue.items == []
    assert created["agent"].run_calls == []


def test_arm_picker_empty_step_id_returns_error(monkeypatch) -> None:
    """arm_picker with an empty string step_id is treated the same as missing."""
    fake_queue, created = _install_stubs(monkeypatch)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "arm_picker", "step_id": ""})
            response = websocket.receive_json()

    assert response["type"] == "error"
    assert "step_id" in response["message"].lower()
    assert fake_queue.items == []
