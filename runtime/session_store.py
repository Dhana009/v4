"""
runtime/session_store.py

Session save/load/restore for replay and versioning.

Source rule: S6-0901–S6-0903.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Spec and State
# ---------------------------------------------------------------------------

@dataclass
class SessionSpec:
    title: str
    steps: list[dict[str, Any]]
    page_url: str


@dataclass
class SessionState:
    session_id: str
    current_step_index: int = 0
    status: str = "ready"


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_STORE: dict[str, SessionSpec] = {}


def save_session(spec: SessionSpec) -> str:
    session_id = str(uuid.uuid4())
    _STORE[session_id] = spec
    return session_id


def load_session(session_id: str) -> SessionSpec | None:
    return _STORE.get(session_id)


def restore_session_state(session_id: str) -> SessionState:
    return SessionState(session_id=session_id)
