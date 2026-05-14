"""
tests/conftest.py — shared test helpers.

E1 (B1) — the WS endpoint now emits an `agent_settings` event immediately
after `ready`. Existing tests that consume exactly one init event then
read a command response would otherwise pick up agent_settings instead of
the response. The helper below drains init events safely.
"""
from __future__ import annotations

_INIT_EVENT_TYPES = frozenset(
    {"status", "ready", "agent_settings", "session_state"}
)


def drain_until_non_init(websocket, max_drain: int = 8):
    """Read and discard init events; return the first non-init event.

    Use this in WS tests after a `websocket.send_json(...)` whose response
    is the first non-init event in the queue.
    """
    for _ in range(max_drain):
        msg = websocket.receive_json()
        if msg.get("type") not in _INIT_EVENT_TYPES:
            return msg
    raise AssertionError(
        f"drain_until_non_init: never saw non-init event after {max_drain} drains"
    )
