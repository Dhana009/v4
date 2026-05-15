"""
runtime/session_store.py

Session save/load/restore for replay and versioning.

Source rules: S6-0901–S6-0903 (in-memory), S7-0109 (file persistence).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Output directory relative to workspace root
_OUTPUT_SUBDIR = "autoworkbench-output"
_RECORDINGS_SUBDIR = "recordings"

# Valid recording_id pattern
_RECORDING_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

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


def _ensure_output_dir(workspace: str | os.PathLike, *subdirs: str) -> Path:
    """Return the output directory path, creating it (and any subdirs) if absent."""
    out = Path(workspace) / _OUTPUT_SUBDIR
    for sub in subdirs:
        out = out / sub
    out.mkdir(parents=True, exist_ok=True)
    return out


def _atomic_write_text(path: Path, text: str) -> None:
    """Write *text* to *path* atomically (temp file + os.replace)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_session_to_file(
    spec: SessionSpec,
    path: str | None = None,
    name: str | None = None,
) -> tuple[str, str]:
    """
    Persist a SessionSpec to a JSON file.

    Returns (path, name) of the saved file.
    When *path* is None the file is written under
    <workspace>/autoworkbench-output/ (created if needed).
    Raises FileNotFoundError if the explicit *path* directory does not exist.
    """
    effective_name = (name or spec.title or "session").strip() or "session"

    if path is None:
        workspace = os.getenv("AUTOWORKBENCH_WORKSPACE", os.getcwd())
        out_dir = _ensure_output_dir(workspace)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        filename = f"{effective_name}_{ts}.json"
        path = str(out_dir / filename)

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

    _atomic_write_text(Path(path), json.dumps(data, indent=2, ensure_ascii=True, default=str))

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


# ---------------------------------------------------------------------------
# SessionStore — versioned recording lifecycle (DG1 G8/G9, P1)
# ---------------------------------------------------------------------------

def _validate_recording_id(recording_id: str) -> None:
    """Raise ValueError if *recording_id* does not match the allowed pattern."""
    if not _RECORDING_ID_RE.fullmatch(recording_id):
        raise ValueError(
            f"recording_id must match ^[A-Za-z0-9_-]{{1,64}}$, got: {recording_id!r}"
        )


class SessionStore:
    """
    File-backed store for versioned recordings.

    All files are written under ``<workspace_root>/autoworkbench-output/``.
    """

    def __init__(self, workspace_root: str | os.PathLike | None = None) -> None:
        if workspace_root is None:
            workspace_root = os.getenv("AUTOWORKBENCH_WORKSPACE", os.getcwd())
        self._workspace = Path(workspace_root)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recordings_dir(self) -> Path:
        """Return (and create) the recordings sub-directory."""
        return _ensure_output_dir(self._workspace, _RECORDINGS_SUBDIR)

    def _existing_versions(self, recording_id: str) -> list[int]:
        """Return sorted list of existing version numbers for *recording_id*."""
        rdir = self._recordings_dir()
        pattern = re.compile(rf"^{re.escape(recording_id)}__v(\d+)\.json$")
        versions: list[int] = []
        for entry in rdir.iterdir():
            m = pattern.fullmatch(entry.name)
            if m:
                versions.append(int(m.group(1)))
        return sorted(versions)

    def _recording_path(self, recording_id: str, version: int) -> Path:
        return self._recordings_dir() / f"{recording_id}__v{version}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_recording(
        self,
        recording_id: str,
        payload: dict,
        version: int | None = None,
    ) -> Path:
        """
        Write *payload* as a versioned recording JSON file.

        If *version* is ``None``, auto-increment from the highest existing
        version on disk (starting at 1 for new recordings).

        Returns the ``Path`` of the written file.
        Raises ``ValueError`` for invalid *recording_id*.
        """
        _validate_recording_id(recording_id)
        if version is None:
            existing = self._existing_versions(recording_id)
            version = (existing[-1] + 1) if existing else 1

        dest = self._recording_path(recording_id, version)
        _atomic_write_text(dest, json.dumps(payload, indent=2, ensure_ascii=True, default=str))
        return dest

    def load_recording(
        self,
        recording_id: str,
        version: int | None = None,
    ) -> dict:
        """
        Load a recording from disk.

        If *version* is ``None``, returns the latest version.
        Raises ``FileNotFoundError`` on a miss.
        Raises ``ValueError`` for invalid *recording_id*.
        """
        _validate_recording_id(recording_id)
        if version is None:
            existing = self._existing_versions(recording_id)
            if not existing:
                raise FileNotFoundError(
                    f"No recordings found for recording_id={recording_id!r}"
                )
            version = existing[-1]

        dest = self._recording_path(recording_id, version)
        if not dest.is_file():
            raise FileNotFoundError(
                f"Recording not found: {dest}"
            )

        with dest.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def list_recordings(self) -> list[dict]:
        """
        Return metadata for all known recordings.

        Each entry is::

            {
                "recording_id": str,
                "latest_version": int,
                "versions": [int, ...],
                "saved_at_iso": str,   # mtime of the latest version file
            }

        Results are sorted by *recording_id*.
        """
        rdir = self._recordings_dir()
        pattern = re.compile(r"^([A-Za-z0-9_-]{1,64})__v(\d+)\.json$")
        by_id: dict[str, list[int]] = {}
        for entry in rdir.iterdir():
            m = pattern.fullmatch(entry.name)
            if m:
                rid, ver = m.group(1), int(m.group(2))
                by_id.setdefault(rid, []).append(ver)

        result: list[dict] = []
        for rid in sorted(by_id):
            versions = sorted(by_id[rid])
            latest = versions[-1]
            latest_path = self._recording_path(rid, latest)
            mtime = datetime.fromtimestamp(
                latest_path.stat().st_mtime, tz=timezone.utc
            ).isoformat()
            result.append(
                {
                    "recording_id": rid,
                    "latest_version": latest,
                    "versions": versions,
                    "saved_at_iso": mtime,
                }
            )
        return result

    def save_repaired_recording(
        self,
        recording_id: str,
        payload: dict,
        repair_note: str,
    ) -> Path:
        """
        Save a repaired version of a recording.

        Bumps the version (same logic as :meth:`save_recording`) and writes a
        sidecar ``<recording_id>__v<N>.repair.txt`` file containing
        *repair_note* plus a UTC timestamp.

        Returns the ``Path`` of the main JSON file.
        Raises ``ValueError`` for invalid *recording_id*.
        """
        _validate_recording_id(recording_id)
        existing = self._existing_versions(recording_id)
        new_version = (existing[-1] + 1) if existing else 1

        dest = self._recording_path(recording_id, new_version)
        sidecar = dest.with_suffix(".repair.txt")

        ts = datetime.now(timezone.utc).isoformat()
        sidecar_text = f"repair_note: {repair_note}\nutc_timestamp: {ts}\n"

        _atomic_write_text(dest, json.dumps(payload, indent=2, ensure_ascii=True, default=str))
        _atomic_write_text(sidecar, sidecar_text)

        return dest
