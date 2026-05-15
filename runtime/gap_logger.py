"""Workspace-persisted capability gap logger.

Per Complete LLM Mode P0 §25 and scenarios §13 (Scenario 8: capability gap).
Append-only JSONL record of capability gaps surfaced by agent/classifier/executor
during a workspace run. A later wave wires this into agent.py recording paths.

Schema (required fields validated in :meth:`GapLogger.record`):
    url: str
    user_intent: str
    operation_id: str | None
    needed_capability: str
    available_tools: list[str]
    severity: "info" | "warn" | "error"
    source: "agent" | "classifier" | "executor" | "user"
    phase: str

Optional: step_id, suggested_future_work, message

Auto-filled per record:
    ordinal: int (1-indexed sequence per file)
    recorded_at: UTC ISO8601 with "Z" suffix
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # POSIX advisory file locking. Fall back silently if unavailable.
    import fcntl as _fcntl  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - non-POSIX
    _fcntl = None  # type: ignore[assignment]


_REQUIRED_FIELDS: tuple[str, ...] = (
    "url",
    "user_intent",
    "operation_id",
    "needed_capability",
    "available_tools",
    "severity",
    "source",
    "phase",
)

_REQUIRED_STR_FIELDS: frozenset[str] = frozenset(
    {"url", "user_intent", "needed_capability", "phase"}
)

_ALLOWED_SEVERITY: frozenset[str] = frozenset({"info", "warn", "error"})
_ALLOWED_SOURCE: frozenset[str] = frozenset({"agent", "classifier", "executor", "user"})

_OPTIONAL_FIELDS: frozenset[str] = frozenset(
    {"step_id", "suggested_future_work", "message"}
)

_OUTPUT_SUBDIR = "autoworkbench-output"
_LOG_FILENAME = "capability_gaps.jsonl"


class GapLogger:
    """Append-only capability gap log persisted under the workspace root."""

    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        self._workspace_root = Path(workspace_root)
        self._output_dir = self._workspace_root / _OUTPUT_SUBDIR
        self._path = self._output_dir / _LOG_FILENAME
        self._process_lock = threading.Lock()
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        """Filesystem path of the JSONL log."""
        return self._path

    def record(self, gap: dict[str, Any]) -> dict[str, Any]:
        """Validate ``gap`` and append a single JSON line. Returns the persisted record."""
        if not isinstance(gap, dict):
            raise ValueError("gap must be a dict")

        self._validate(gap)

        record: dict[str, Any] = {}
        for field in _REQUIRED_FIELDS:
            record[field] = gap[field]
        for field in _OPTIONAL_FIELDS:
            if field in gap:
                record[field] = gap[field]

        with self._process_lock:
            ordinal = self._next_ordinal()
            record["ordinal"] = ordinal
            record["recorded_at"] = self._utc_now_iso()
            line = json.dumps(record, ensure_ascii=False, sort_keys=False)
            self._append_line(line)

        return record

    def read_all(self) -> list[dict[str, Any]]:
        """Return all persisted records. Small files only (P0)."""
        if not self._path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                rows.append(json.loads(raw))
        return rows

    def clear(self) -> None:
        """Remove the log file. Intended for tests."""
        with self._process_lock:
            try:
                self._path.unlink()
            except FileNotFoundError:
                pass

    # ------------------------------------------------------------------ internals

    @staticmethod
    def _validate(gap: dict[str, Any]) -> None:
        for field in _REQUIRED_FIELDS:
            if field not in gap:
                raise ValueError(f"missing required field: {field}")

        for field in _REQUIRED_STR_FIELDS:
            value = gap[field]
            if not isinstance(value, str) or not value:
                raise ValueError(f"field {field} must be a non-empty string")

        op_id = gap["operation_id"]
        if op_id is not None and not isinstance(op_id, str):
            raise ValueError("field operation_id must be str or None")

        tools = gap["available_tools"]
        if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
            raise ValueError("field available_tools must be a list[str]")

        severity = gap["severity"]
        if severity not in _ALLOWED_SEVERITY:
            raise ValueError(
                f"field severity must be one of {sorted(_ALLOWED_SEVERITY)}"
            )

        source = gap["source"]
        if source not in _ALLOWED_SOURCE:
            raise ValueError(f"field source must be one of {sorted(_ALLOWED_SOURCE)}")

    def _next_ordinal(self) -> int:
        if not self._path.exists():
            return 1
        count = 0
        with self._path.open("rb") as fh:
            for line in fh:
                if line.strip():
                    count += 1
        return count + 1

    def _append_line(self, line: str) -> None:
        # Ensure parent dir survives external cleanup between calls.
        self._output_dir.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            locked = False
            if _fcntl is not None:
                try:
                    _fcntl.flock(fh.fileno(), _fcntl.LOCK_EX)
                    locked = True
                except OSError:
                    locked = False
            try:
                fh.write(line)
                fh.write("\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except OSError:
                    pass
            finally:
                if locked and _fcntl is not None:
                    try:
                        _fcntl.flock(fh.fileno(), _fcntl.LOCK_UN)
                    except OSError:
                        pass

    @staticmethod
    def _utc_now_iso() -> str:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["GapLogger"]
