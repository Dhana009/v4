"""Unit tests for runtime.session_store.SessionStore recording versioning."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from runtime.session_store import SessionStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store() -> tuple[SessionStore, Path]:
    """Return a SessionStore backed by a temporary directory."""
    tmp = tempfile.mkdtemp()
    return SessionStore(workspace_root=tmp), Path(tmp)


# ---------------------------------------------------------------------------
# 1. save_recording auto-increments version
# ---------------------------------------------------------------------------

def test_save_recording_auto_increments() -> None:
    store, _ = _make_store()
    p1 = store.save_recording("rec1", {"step": 1})
    p2 = store.save_recording("rec1", {"step": 2})
    assert "__v1." in p1.name
    assert "__v2." in p2.name


# ---------------------------------------------------------------------------
# 2. load_recording returns latest version by default
# ---------------------------------------------------------------------------

def test_load_recording_latest() -> None:
    store, _ = _make_store()
    store.save_recording("recA", {"v": 1})
    store.save_recording("recA", {"v": 2})
    data = store.load_recording("recA")
    assert data["v"] == 2


# ---------------------------------------------------------------------------
# 3. Explicit version mismatch raises FileNotFoundError
# ---------------------------------------------------------------------------

def test_load_nonexistent_version_raises() -> None:
    store, _ = _make_store()
    store.save_recording("recB", {"v": 1})
    with pytest.raises(FileNotFoundError):
        store.load_recording("recB", version=99)


# ---------------------------------------------------------------------------
# 4. save_repaired_recording creates .repair.txt sidecar
# ---------------------------------------------------------------------------

def test_save_repaired_recording_creates_sidecar() -> None:
    store, _ = _make_store()
    dest = store.save_repaired_recording("recC", {"repaired": True}, "fixed locator")
    sidecar = dest.with_suffix(".repair.txt")
    assert sidecar.is_file()
    content = sidecar.read_text(encoding="utf-8")
    assert "fixed locator" in content


# ---------------------------------------------------------------------------
# 5. Invalid recording_id raises ValueError
# ---------------------------------------------------------------------------

def test_invalid_recording_id_raises() -> None:
    store, _ = _make_store()
    with pytest.raises(ValueError, match="recording_id"):
        store.save_recording("bad id with spaces!", {"x": 1})


# ---------------------------------------------------------------------------
# 6. list_recordings shape
# ---------------------------------------------------------------------------

def test_list_recordings_shape() -> None:
    store, _ = _make_store()
    store.save_recording("alpha", {"n": 1})
    store.save_recording("alpha", {"n": 2})
    store.save_recording("beta", {"n": 1})
    recordings = store.list_recordings()
    assert isinstance(recordings, list)
    assert len(recordings) == 2
    ids = [r["recording_id"] for r in recordings]
    assert "alpha" in ids
    assert "beta" in ids
    for entry in recordings:
        assert "latest_version" in entry
        assert "versions" in entry
        assert "saved_at_iso" in entry


# ---------------------------------------------------------------------------
# 7. load_recording raises FileNotFoundError when no recordings exist
# ---------------------------------------------------------------------------

def test_load_recording_no_recordings_raises() -> None:
    store, _ = _make_store()
    with pytest.raises(FileNotFoundError):
        store.load_recording("missing_rec")


# ---------------------------------------------------------------------------
# 8. save_repaired_recording increments on top of existing versions
# ---------------------------------------------------------------------------

def test_save_repaired_recording_increments_version() -> None:
    store, _ = _make_store()
    store.save_recording("recD", {"v": 1})
    dest = store.save_repaired_recording("recD", {"v": 2, "repaired": True}, "patch note")
    assert "__v2." in dest.name
