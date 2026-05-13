"""
runtime/session_store.py

Session save/load/restore for replay and versioning.

Source rules: S6-0901–S6-0903 (in-memory), S7-0109 (file persistence).
"""
from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Spec and State
# ---------------------------------------------------------------------------

@dataclass
class SessionSpec:
    title: str
    steps: list[dict[str, Any]]
    page_url: str
    # Sprint 7 Cluster 1 — S7-0109: extended fields for round-trip persistence
    recorded_steps: list[dict[str, Any]] = field(default_factory=list)
    code_preview: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


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


# ---------------------------------------------------------------------------
# Sprint 7 Cluster 1 — S7-0109: file persistence
# Fields that must NOT be saved (security): api_keys, raw_dom_snapshots
# ---------------------------------------------------------------------------

_EXCLUDED_STEP_FIELDS = {"dom_snapshot", "page_snapshot", "raw_html", "api_key", "secret", "token"}


def _sanitize_step(step: dict[str, Any]) -> dict[str, Any]:
    """Remove security-sensitive fields from a step before saving."""
    return {k: v for k, v in step.items() if k not in _EXCLUDED_STEP_FIELDS}


def _validate_spec_dict(data: dict[str, Any]) -> None:
    """Validate a loaded session dict against the minimum required schema."""
    if not isinstance(data, dict):
        raise ValueError("Session file must contain a JSON object")
    if "title" not in data:
        raise ValueError("Session file missing required field: title")
    if "steps" not in data:
        raise ValueError("Session file missing required field: steps")
    if not isinstance(data["steps"], list):
        raise TypeError("Session 'steps' field must be a list")
    if "page_url" not in data:
        raise ValueError("Session file missing required field: page_url")


def save_session_to_file(
    spec: SessionSpec,
    path: str | None = None,
    name: str | None = None,
) -> tuple[str, str]:
    """
    Persist a SessionSpec to a JSON file.

    Returns (path, name) of the saved file.
    Raises OSError / FileNotFoundError if the path directory does not exist.
    """
    effective_name = (name or spec.title or "session").strip() or "session"

    if path is None:
        workspace = os.getenv("AUTOWORKBENCH_WORKSPACE", os.getcwd())
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        filename = f"{effective_name}_{ts}.json"
        path = os.path.join(workspace, filename)

    # Validate that the parent directory exists
    parent_dir = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent_dir):
        raise FileNotFoundError(f"Directory does not exist: {parent_dir}")

    sanitized_steps = [_sanitize_step(s) for s in (spec.steps or [])]
    sanitized_recorded = [_sanitize_step(s) for s in (spec.recorded_steps or [])]

    data: dict[str, Any] = {
        "title": spec.title,
        "steps": sanitized_steps,
        "page_url": spec.page_url,
        "recorded_steps": sanitized_recorded,
        "code_preview": spec.code_preview,
        "session_id": spec.session_id,
        "metadata": deepcopy(spec.metadata or {}),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "session.v1",
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=True, default=str)

    return path, effective_name


def load_session_from_file(path: str) -> SessionSpec:
    """
    Load a SessionSpec from a JSON file.

    Raises FileNotFoundError if path does not exist.
    Raises ValueError if JSON is malformed or required fields are missing.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Session file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Session file is not valid JSON: {exc}") from exc

    _validate_spec_dict(data)

    return SessionSpec(
        title=str(data["title"]),
        steps=list(data["steps"]),
        page_url=str(data["page_url"]),
        recorded_steps=list(data.get("recorded_steps") or []),
        code_preview=data.get("code_preview"),
        session_id=data.get("session_id"),
        metadata=dict(data.get("metadata") or {}),
    )
