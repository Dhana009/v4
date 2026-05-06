from __future__ import annotations

import asyncio
import threading
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server


def test_transient_websocket_disconnect_preserves_active_run(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setattr(server.app.state, "active_run_session", None, raising=False)

    started = threading.Event()
    resumed = threading.Event()
    finished = threading.Event()
    cancelled = {"value": False}
    created_agents: list[object] = []

    async def fake_launch_browser() -> None:
        return None

    class FakeAgentLoop:
        def __init__(self, ws, control_queue) -> None:
            self._ws = ws
            self.control_queue = control_queue
            self.ws_rebind_count = 0
            self.llm = SimpleNamespace(reset=lambda: None)
            created_agents.append(self)

        @property
        def ws(self):  # noqa: D401 - simple test helper property
            return self._ws

        @ws.setter
        def ws(self, value) -> None:
            self._ws = value
            self.ws_rebind_count += 1

        async def run(self, steps) -> None:  # noqa: ARG002
            started.set()
            try:
                await asyncio.to_thread(resumed.wait)
                await self.ws.send_json({"type": "status", "message": "run completed"})
                finished.set()
            except asyncio.CancelledError:
                cancelled["value"] = True
                raise

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as first_ws:
            initial = first_ws.receive_json()
            assert initial["type"] == "status"
            assert "Browser launched" in initial["message"]

            first_ws.send_json({"type": "run_steps", "steps": [{"step_id": "step-1"}]})
            assert started.wait(timeout=1.0)

        time.sleep(0.1)
        assert cancelled["value"] is False
        assert len(created_agents) == 1

        with client.websocket_connect("/ws") as second_ws:
            reconnect_status = second_ws.receive_json()
            assert reconnect_status["type"] == "status"
            assert "Browser launched" in reconnect_status["message"]

            assert created_agents[0].ws_rebind_count == 1
            resumed.set()
            assert finished.wait(timeout=1.0)
            completed_status = second_ws.receive_json()
            assert completed_status["type"] == "status"
            assert completed_status["message"] == "run completed"

    assert cancelled["value"] is False
    assert len(created_agents) == 1
