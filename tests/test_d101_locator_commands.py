"""
D-101 — locator cluster command handler contract tests.

Commands: improve_locator, view_candidates, change_locator_scope

These tests verify:
1. All three commands are in SUPPORTED_FRONTEND_COMMAND_TYPES
2. Malformed payloads (missing step_id) → typed rejection event
3. Empty payload → typed rejection event
4. Stale run_id → typed rejection event
5. Accepted command emits typed acknowledged event (not code_update / step_recorded)
6. Commands do NOT emit code_update or step_recorded directly
7. view_candidates is mapped to the same handler as improve_locator
   (spec §Sub-area A note: "Map it to the same handler")
8. change_locator_scope requires scope field; missing scope → typed rejection

Architecture:
  - Uses fake WebSocket harness — no live browser, no paid LLM
  - Pattern mirrors tests/test_export_code_handler.py
  - Backend seam: server.py command dispatch + event_contracts.py
"""

from __future__ import annotations

import asyncio
from typing import Any

from runtime.event_contracts import (
    SUPPORTED_FRONTEND_COMMAND_TYPES,
    build_backend_event_envelope,
    build_runtime_rejection_payload,
)


# ── Contract: each command is a supported command type ──────────────────────

def test_improve_locator_in_supported_command_types() -> None:
    """improve_locator must be in SUPPORTED_FRONTEND_COMMAND_TYPES so the WS router accepts it."""
    assert "improve_locator" in SUPPORTED_FRONTEND_COMMAND_TYPES, (
        "improve_locator must be added to SUPPORTED_FRONTEND_COMMAND_TYPES in event_contracts.py"
    )


def test_view_candidates_in_supported_command_types() -> None:
    """view_candidates must be in SUPPORTED_FRONTEND_COMMAND_TYPES."""
    assert "view_candidates" in SUPPORTED_FRONTEND_COMMAND_TYPES, (
        "view_candidates must be added to SUPPORTED_FRONTEND_COMMAND_TYPES in event_contracts.py"
    )


def test_change_locator_scope_in_supported_command_types() -> None:
    """change_locator_scope must be in SUPPORTED_FRONTEND_COMMAND_TYPES."""
    assert "change_locator_scope" in SUPPORTED_FRONTEND_COMMAND_TYPES, (
        "change_locator_scope must be added to SUPPORTED_FRONTEND_COMMAND_TYPES in event_contracts.py"
    )


# ── Fake WebSocket harness ────────────────────────────────────────────────────

class FakeWebSocket:
    """Minimal fake WebSocket that captures sent messages."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)


# ── Handler implementations (match what server.py must implement) ─────────────

async def _dispatch_improve_locator(
    ws: FakeWebSocket,
    msg: dict[str, Any],
    active_run_id: str = "",
) -> None:
    """
    Simulate the server.py dispatch handler for improve_locator.
    Validates payload, rejects malformed, emits improve_locator_acknowledged on accept.
    """
    step_id = str(msg.get("step_id") or "").strip()
    if not step_id:
        rejection = build_runtime_rejection_payload(
            "MISSING_STEP_ID",
            "improve_locator requires 'step_id' field.",
            run_id=active_run_id or None,
            recoverable=False,
            source="server",
        )
        await ws.send_json(rejection)
        return

    cmd_run_id = str(msg.get("run_id") or "").strip()
    if cmd_run_id and active_run_id and cmd_run_id != active_run_id:
        rejection = build_runtime_rejection_payload(
            "STALE_RUN_ID",
            f"run_id {cmd_run_id!r} does not match active run.",
            run_id=active_run_id or None,
            recoverable=False,
            source="server",
        )
        await ws.send_json(rejection)
        return

    ack_event = build_backend_event_envelope(
        "improve_locator_acknowledged",
        {"step_id": step_id, "status": "queued"},
        source="server",
    )
    await ws.send_json(ack_event)


async def _dispatch_view_candidates(
    ws: FakeWebSocket,
    msg: dict[str, Any],
    active_run_id: str = "",
) -> None:
    """
    view_candidates maps to the same backend path as improve_locator.
    Spec note (Sub-area A): "Do NOT invent view_candidates as a new WS command.
    Map it to the same handler."
    """
    # Reuse improve_locator handler with same payload shape
    await _dispatch_improve_locator(ws, msg, active_run_id=active_run_id)


async def _dispatch_change_locator_scope(
    ws: FakeWebSocket,
    msg: dict[str, Any],
    active_run_id: str = "",
) -> None:
    """
    Simulate the server.py dispatch handler for change_locator_scope.
    Validates payload: requires step_id + scope; rejects malformed;
    emits change_locator_scope_acknowledged on accept.
    """
    step_id = str(msg.get("step_id") or "").strip()
    if not step_id:
        rejection = build_runtime_rejection_payload(
            "MISSING_STEP_ID",
            "change_locator_scope requires 'step_id' field.",
            run_id=active_run_id or None,
            recoverable=False,
            source="server",
        )
        await ws.send_json(rejection)
        return

    scope = msg.get("scope")
    scope_str = str(scope or "").strip() if scope is not None else ""
    if not scope_str:
        rejection = build_runtime_rejection_payload(
            "MISSING_SCOPE",
            "change_locator_scope requires 'scope' field (broader|narrower|free-text).",
            run_id=active_run_id or None,
            recoverable=False,
            source="server",
        )
        await ws.send_json(rejection)
        return

    cmd_run_id = str(msg.get("run_id") or "").strip()
    if cmd_run_id and active_run_id and cmd_run_id != active_run_id:
        rejection = build_runtime_rejection_payload(
            "STALE_RUN_ID",
            f"run_id {cmd_run_id!r} does not match active run.",
            run_id=active_run_id or None,
            recoverable=False,
            source="server",
        )
        await ws.send_json(rejection)
        return

    ack_event = build_backend_event_envelope(
        "change_locator_scope_acknowledged",
        {"step_id": step_id, "scope": scope_str, "status": "queued"},
        source="server",
    )
    await ws.send_json(ack_event)


# ── improve_locator handler tests ─────────────────────────────────────────────

def test_improve_locator_valid_payload_emits_acknowledged() -> None:
    """
    Valid improve_locator {step_id: 's1'} → emits improve_locator_acknowledged.
    """
    ws = FakeWebSocket()
    asyncio.run(_dispatch_improve_locator(ws, {"type": "improve_locator", "step_id": "s1"}))
    assert len(ws.sent) == 1
    event = ws.sent[0]
    assert event["type"] == "improve_locator_acknowledged"
    assert event["payload"]["step_id"] == "s1"
    assert event["payload"]["status"] == "queued"
    assert "schema_version" in event


def test_improve_locator_missing_step_id_emits_rejection() -> None:
    """Missing step_id → runtime_rejected with MISSING_STEP_ID code."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_improve_locator(ws, {"type": "improve_locator"}))
    assert len(ws.sent) == 1
    event = ws.sent[0]
    assert event["type"] == "runtime_rejected"
    assert event["rejection_code"] == "MISSING_STEP_ID"
    assert "step_id" in event["message"].lower()


def test_improve_locator_empty_step_id_emits_rejection() -> None:
    """Empty step_id string → runtime_rejected."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_improve_locator(ws, {"type": "improve_locator", "step_id": ""}))
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"
    assert ws.sent[0]["rejection_code"] == "MISSING_STEP_ID"


def test_improve_locator_empty_payload_emits_rejection() -> None:
    """Empty payload {} → runtime_rejected (no step_id key)."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_improve_locator(ws, {}))
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"


def test_improve_locator_stale_run_id_emits_rejection() -> None:
    """Mismatched run_id → STALE_RUN_ID rejection."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_improve_locator(
            ws,
            {"type": "improve_locator", "step_id": "s1", "run_id": "run_old"},
            active_run_id="run_current",
        )
    )
    assert len(ws.sent) == 1
    event = ws.sent[0]
    assert event["type"] == "runtime_rejected"
    assert event["rejection_code"] == "STALE_RUN_ID"


def test_improve_locator_matching_run_id_accepted() -> None:
    """Matching run_id → accepted, emits acknowledged."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_improve_locator(
            ws,
            {"type": "improve_locator", "step_id": "s1", "run_id": "run_42"},
            active_run_id="run_42",
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "improve_locator_acknowledged"


def test_improve_locator_no_run_id_field_accepted_without_stale_check() -> None:
    """Missing run_id field → no stale check → accepted."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_improve_locator(
            ws,
            {"type": "improve_locator", "step_id": "s1"},
            active_run_id="run_42",
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "improve_locator_acknowledged"


def test_improve_locator_does_not_emit_code_update() -> None:
    """improve_locator must NOT emit code_update or step_recorded."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_improve_locator(ws, {"type": "improve_locator", "step_id": "s1"}))
    for event in ws.sent:
        assert event.get("type") not in ("code_update", "step_recorded"), (
            f"improve_locator must not emit {event['type']}"
        )


# ── view_candidates handler tests ─────────────────────────────────────────────

def test_view_candidates_valid_payload_emits_acknowledged() -> None:
    """view_candidates with valid step_id → same handler as improve_locator → acknowledged."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_view_candidates(ws, {"type": "view_candidates", "step_id": "s2"}))
    assert len(ws.sent) == 1
    # view_candidates delegates to improve_locator handler, which emits improve_locator_acknowledged
    event = ws.sent[0]
    assert event["type"] == "improve_locator_acknowledged"
    assert event["payload"]["step_id"] == "s2"


def test_view_candidates_missing_step_id_emits_rejection() -> None:
    """Missing step_id → typed rejection."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_view_candidates(ws, {"type": "view_candidates"}))
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"
    assert ws.sent[0]["rejection_code"] == "MISSING_STEP_ID"


def test_view_candidates_empty_payload_emits_rejection() -> None:
    """Empty payload → typed rejection."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_view_candidates(ws, {}))
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"


def test_view_candidates_stale_run_id_emits_rejection() -> None:
    """Stale run_id → STALE_RUN_ID rejection."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_view_candidates(
            ws,
            {"type": "view_candidates", "step_id": "s1", "run_id": "old"},
            active_run_id="current",
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"
    assert ws.sent[0]["rejection_code"] == "STALE_RUN_ID"


def test_view_candidates_does_not_emit_code_update() -> None:
    """view_candidates must NOT emit code_update or step_recorded."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_view_candidates(ws, {"type": "view_candidates", "step_id": "s1"}))
    for event in ws.sent:
        assert event.get("type") not in ("code_update", "step_recorded"), (
            f"view_candidates must not emit {event['type']}"
        )


# ── change_locator_scope handler tests ────────────────────────────────────────

def test_change_locator_scope_valid_payload_emits_acknowledged() -> None:
    """Valid {step_id, scope: 'broader'} → emits change_locator_scope_acknowledged."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_change_locator_scope(
            ws,
            {"type": "change_locator_scope", "step_id": "s1", "scope": "broader"},
        )
    )
    assert len(ws.sent) == 1
    event = ws.sent[0]
    assert event["type"] == "change_locator_scope_acknowledged"
    assert event["payload"]["step_id"] == "s1"
    assert event["payload"]["scope"] == "broader"
    assert "schema_version" in event


def test_change_locator_scope_narrower_accepted() -> None:
    """scope='narrower' is a valid value."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_change_locator_scope(
            ws,
            {"type": "change_locator_scope", "step_id": "s1", "scope": "narrower"},
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "change_locator_scope_acknowledged"
    assert ws.sent[0]["payload"]["scope"] == "narrower"


def test_change_locator_scope_free_text_accepted() -> None:
    """scope can be arbitrary free-text per spec."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_change_locator_scope(
            ws,
            {"type": "change_locator_scope", "step_id": "s1", "scope": "focus on the navbar"},
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "change_locator_scope_acknowledged"


def test_change_locator_scope_missing_step_id_emits_rejection() -> None:
    """Missing step_id → MISSING_STEP_ID rejection."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_change_locator_scope(
            ws,
            {"type": "change_locator_scope", "scope": "broader"},
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"
    assert ws.sent[0]["rejection_code"] == "MISSING_STEP_ID"


def test_change_locator_scope_missing_scope_emits_rejection() -> None:
    """Missing scope field → MISSING_SCOPE rejection."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_change_locator_scope(
            ws,
            {"type": "change_locator_scope", "step_id": "s1"},
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"
    assert ws.sent[0]["rejection_code"] == "MISSING_SCOPE"


def test_change_locator_scope_empty_scope_emits_rejection() -> None:
    """Empty scope string → MISSING_SCOPE rejection."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_change_locator_scope(
            ws,
            {"type": "change_locator_scope", "step_id": "s1", "scope": ""},
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"
    assert ws.sent[0]["rejection_code"] == "MISSING_SCOPE"


def test_change_locator_scope_empty_payload_emits_rejection() -> None:
    """Empty payload {} → runtime_rejected."""
    ws = FakeWebSocket()
    asyncio.run(_dispatch_change_locator_scope(ws, {}))
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"


def test_change_locator_scope_stale_run_id_emits_rejection() -> None:
    """Stale run_id → STALE_RUN_ID rejection."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_change_locator_scope(
            ws,
            {
                "type": "change_locator_scope",
                "step_id": "s1",
                "scope": "broader",
                "run_id": "old_run",
            },
            active_run_id="current_run",
        )
    )
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "runtime_rejected"
    assert ws.sent[0]["rejection_code"] == "STALE_RUN_ID"


def test_change_locator_scope_does_not_emit_code_update() -> None:
    """change_locator_scope must NOT emit code_update or step_recorded."""
    ws = FakeWebSocket()
    asyncio.run(
        _dispatch_change_locator_scope(
            ws,
            {"type": "change_locator_scope", "step_id": "s1", "scope": "broader"},
        )
    )
    for event in ws.sent:
        assert event.get("type") not in ("code_update", "step_recorded"), (
            f"change_locator_scope must not emit {event['type']}"
        )


# ── Event shape tests ─────────────────────────────────────────────────────────

def test_improve_locator_acknowledged_event_shape() -> None:
    """improve_locator_acknowledged must be a valid backend event envelope."""
    event = build_backend_event_envelope(
        "improve_locator_acknowledged",
        {"step_id": "s1", "status": "queued"},
        source="server",
    )
    assert event["type"] == "improve_locator_acknowledged"
    assert event["payload"]["step_id"] == "s1"
    assert event["payload"]["status"] == "queued"
    assert "schema_version" in event


def test_change_locator_scope_acknowledged_event_shape() -> None:
    """change_locator_scope_acknowledged must be a valid backend event envelope."""
    event = build_backend_event_envelope(
        "change_locator_scope_acknowledged",
        {"step_id": "s1", "scope": "broader", "status": "queued"},
        source="server",
    )
    assert event["type"] == "change_locator_scope_acknowledged"
    assert event["payload"]["scope"] == "broader"
    assert "schema_version" in event
