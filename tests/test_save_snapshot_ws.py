from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import server
from runtime.event_contracts import BACKEND_EVENT_SCHEMA_VERSION


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
            "steps": [
                {
                    "number": 1,
                    "action": "assert",
                    "element_name": "Get started",
                    "expected_outcome": {
                        "type": "navigation",
                        "description": "goes to docs intro page",
                        "source": "user",
                        "required": True,
                    },
                }
            ],
        },
        "recorded_steps": [
            {
                "step_id": "step-1",
                "step_number": 1,
                "intent": "Check that Get started is visible and click it",
                "expected_outcome": {
                    "type": "navigation",
                    "description": "goes to docs intro page",
                    "source": "user",
                    "required": True,
                },
                "generated_line": "await expect(getStarted).toBeVisible();",
                "children": [],
            }
        ],
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
            websocket.receive_json()  # E1/B1 drain agent_settings
            websocket.receive_json()  # E3/B5 drain endpoint_registry
            assert initial_message["type"] in {"status", "ready"}

            websocket.send_json({"type": "save_snapshot"})
            response = websocket.receive_json()

    assert response["type"] == "save_snapshot_result"
    assert response["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    assert response["ok"] is True
    assert response["payload"]["ok"] is True
    assert response["payload"]["snapshot"] == snapshot
    assert response["snapshot"] == snapshot
    assert response["snapshot"]["plan_ready"]["steps"][0]["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    assert response["snapshot"]["recorded_steps"][0]["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == []


def test_save_snapshot_ws_returns_safe_failure_message(monkeypatch) -> None:
    fake_queue, created = _install_server_stubs(monkeypatch, error=RuntimeError("boom"))

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()  # E1/B1 drain agent_settings
            websocket.receive_json()  # E3/B5 drain endpoint_registry
            websocket.send_json({"type": "save_snapshot"})
            response = websocket.receive_json()

    assert response["type"] == "save_snapshot_result"
    assert response["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    assert response["ok"] is False
    assert response["payload"]["ok"] is False
    assert response["payload"]["error"] == "Snapshot save failed: RuntimeError"
    assert response["error"] == "Snapshot save failed: RuntimeError"
    assert created["agent"].control_queue is fake_queue
    assert fake_queue.items == []
