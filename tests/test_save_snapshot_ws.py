from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import server


class FakeQueue:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    async def put(self, item: dict[str, object]) -> None:
        self.items.append(item)


def _install_server_stubs(monkeypatch, snapshot: dict[str, object] | None = None, error: Exception | None = None):
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
            created["agent"] = self

        async def run(self, steps) -> None:  # noqa: ARG002
            return None

        def _build_spec_snapshot(self) -> dict[str, object]:
            if error is not None:
                raise error
            return dict(snapshot or {})

    monkeypatch.setattr(server, "launch_browser", fake_launch_browser)
    monkeypatch.setattr(server, "AgentLoop", FakeAgentLoop)
    monkeypatch.setattr(server.asyncio, "Queue", lambda: fake_queue)

    return fake_queue, created


def test_save_snapshot_ws_returns_snapshot_and_skips_control_queue(monkeypatch) -> None:
    snapshot = {
        "schema_version": "autoworkbench.spec.v1",
        "session_id": "run-test-001",
        "created_at": "2026-05-02T00:00:00+00:00",
        "original_user_intent": "Check that Get started is visible and click it",
        "plan_ready": {
            "summary": "I will check that Get started is visible and click it",
            "steps": [],
        },
        "recorded_steps": [],
        "code": {"lines": [], "full_spec_preview": ""},
        "capability_gaps": [],
        "metadata": {
            "phase": "executing",
            "completed_step_count": 0,
            "recorded_step_count": 0,
        },
    }
    fake_queue, created = _install_server_stubs(monkeypatch, snapshot=snapshot)

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            initial_message = websocket.receive_json()
            assert initial_message["type"] == "status"
            assert "Browser launched" in initial_message["message"]

            websocket.send_json({"type": "save_snapshot"})
            response = websocket.receive_json()

    assert response["type"] == "save_snapshot_result"
    assert response["ok"] is True
    assert response["snapshot"] == snapshot
    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == []


def test_save_snapshot_ws_returns_safe_failure_message(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch, error=RuntimeError("boom"))

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "save_snapshot"})
            response = websocket.receive_json()

    assert response["type"] == "save_snapshot_result"
    assert response["ok"] is False
    assert response["error"] == "Snapshot save failed: RuntimeError"
    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == []

