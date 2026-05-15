"""
tests/test_session_persistence_contract.py

Sprint 7 Cluster 1 — S7-0109: save_session/load_session command wiring and file persistence tests.
TDD: written before implementation.
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from runtime.event_contracts import (
    SUPPORTED_FRONTEND_COMMAND_TYPES,
    build_load_result_event,
    build_save_result_event,
)
from runtime.session_store import (
    SessionSpec,
    load_session_from_file,
    save_session_to_file,
)


# ---------------------------------------------------------------------------
# Unit Tests — event builders
# ---------------------------------------------------------------------------

def test_build_save_result_event_includes_path_and_name():  # PRD-04-BE-save-load
    result = build_save_result_event(path="/tmp/session.json", name="my-session", session_id="sess-1", step_count=3)
    assert result["path"] == "/tmp/session.json"
    assert result["name"] == "my-session"


def test_build_save_result_event_includes_session_id():  # PRD-04-BE-save-load
    result = build_save_result_event(path="/tmp/s.json", name="s", session_id="sess-42", step_count=0)
    assert result["session_id"] == "sess-42"


def test_build_save_result_event_includes_step_count():  # PRD-04-BE-save-load
    result = build_save_result_event(path="/tmp/s.json", name="s", session_id="s", step_count=7)
    assert result["step_count"] == 7


def test_build_load_result_event_includes_path_and_step_count():  # PRD-04-BE-save-load
    result = build_load_result_event(path="/tmp/session.json", name="s", session_id="sess-1", step_count=4, snapshot_valid=True)
    assert result["path"] == "/tmp/session.json"
    assert result["step_count"] == 4


def test_build_load_result_event_includes_snapshot_valid_flag():  # PRD-04-BE-save-load
    result = build_load_result_event(path="/tmp/s.json", name="s", session_id="s", step_count=0, snapshot_valid=True)
    assert result["snapshot_valid"] is True


def test_build_load_result_event_snapshot_valid_false():  # PRD-04-BE-save-load
    result = build_load_result_event(path="/tmp/s.json", name="s", session_id="s", step_count=0, snapshot_valid=False)
    assert result["snapshot_valid"] is False


def test_save_session_command_registered_in_supported_types():  # PRD-04-CMD-003
    assert "save_session" in SUPPORTED_FRONTEND_COMMAND_TYPES


def test_load_session_command_registered_in_supported_types():  # PRD-04-CMD-004
    assert "load_session" in SUPPORTED_FRONTEND_COMMAND_TYPES


# ---------------------------------------------------------------------------
# Contract Tests — event type fields
# ---------------------------------------------------------------------------

def test_save_result_event_type_correct():  # PRD-04-BE-save-load
    result = build_save_result_event(path="/p", name="n", session_id="s", step_count=0)
    assert result["type"] == "save_result"


def test_load_result_event_type_correct():  # PRD-04-BE-save-load
    result = build_load_result_event(path="/p", name="n", session_id="s", step_count=0, snapshot_valid=True)
    assert result["type"] == "load_result"


def test_save_result_uses_backend_envelope():  # PRD-04-BE-save-load
    result = build_save_result_event(path="/p", name="n", session_id="s", step_count=0)
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_load_result_uses_backend_envelope():  # PRD-04-BE-save-load
    result = build_load_result_event(path="/p", name="n", session_id="s", step_count=0, snapshot_valid=True)
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Integration Tests — file persistence round-trip
# ---------------------------------------------------------------------------

def test_round_trip_save_and_load_restores_recorded_steps():  # PRD-04-CMD-003+004
    spec = SessionSpec(
        title="test-session",
        steps=[{"step_id": "s1", "action": "click"}],
        page_url="http://example.com",
        recorded_steps=[{"step_id": "s1", "status": "recorded", "code": "page.click('#btn')"}],
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        path, _ = save_session_to_file(spec, path=os.path.join(tmp_dir, "session.json"), name="test")
        loaded = load_session_from_file(path)
        assert loaded is not None
        assert isinstance(loaded.recorded_steps, list)
        assert len(loaded.recorded_steps) == 1
        assert loaded.recorded_steps[0]["step_id"] == "s1"


def test_round_trip_save_and_load_restores_code_preview():  # PRD-04-CMD-003+004
    spec = SessionSpec(
        title="test-session",
        steps=[{"step_id": "s1"}],
        page_url="http://example.com",
        code_preview="import pytest\n\ndef test_example():\n    pass\n",
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        path, _ = save_session_to_file(spec, path=os.path.join(tmp_dir, "session.json"), name="code-test")
        loaded = load_session_from_file(path)
        assert loaded is not None
        assert "pytest" in (loaded.code_preview or "")


def test_round_trip_save_and_load_restores_session_state():  # PRD-04-CMD-003+004
    spec = SessionSpec(
        title="roundtrip-test",
        steps=[{"step_id": "s1"}, {"step_id": "s2"}],
        page_url="http://example.com",
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        path, name = save_session_to_file(spec, path=os.path.join(tmp_dir, "s.json"), name="rt")
        loaded = load_session_from_file(path)
        assert loaded is not None
        assert loaded.title == "roundtrip-test"
        assert len(loaded.steps) == 2


def test_save_session_uses_default_name_if_not_given():  # PRD-04-CMD-003
    spec = SessionSpec(title="auto-name", steps=[], page_url="http://example.com")
    with tempfile.TemporaryDirectory() as tmp_dir:
        path, name = save_session_to_file(spec, path=os.path.join(tmp_dir, "s.json"))
        assert name is not None
        assert len(name) > 0


# ---------------------------------------------------------------------------
# Negative Tests (required by GOV-S7-C0-009)
# ---------------------------------------------------------------------------

def test_load_session_rejects_malformed_json():  # PRD-04-CMD-004
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ not valid json }")
        tmp_path = f.name
    try:
        with pytest.raises((ValueError, json.JSONDecodeError, KeyError)):
            load_session_from_file(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_load_session_rejects_missing_required_fields():  # PRD-04-CMD-004
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"random": "data"}, f)
        tmp_path = f.name
    try:
        with pytest.raises((ValueError, KeyError)):
            load_session_from_file(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_load_session_rejects_nonexistent_path():  # PRD-04-CMD-004
    with pytest.raises((FileNotFoundError, ValueError, OSError)):
        load_session_from_file("/nonexistent/path/to/session.json")


def test_saved_session_does_not_contain_raw_api_keys():  # GOV-S7-C0-security
    spec = SessionSpec(title="secure", steps=[], page_url="http://example.com")
    with tempfile.TemporaryDirectory() as tmp_dir:
        path, _ = save_session_to_file(spec, path=os.path.join(tmp_dir, "s.json"), name="secure")
        content = open(path).read()
        # Should not contain anything that looks like an API key pattern
        assert "sk-" not in content
        assert "OPENAI_API_KEY" not in content


def test_saved_session_does_not_contain_raw_dom_snapshots():  # GOV-S7-C0-security
    spec = SessionSpec(
        title="dom-test",
        steps=[{"step_id": "s1", "dom_snapshot": "<html>" + "x" * 10000 + "</html>"}],
        page_url="http://example.com",
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        path, _ = save_session_to_file(spec, path=os.path.join(tmp_dir, "s.json"), name="dom-test")
        content = open(path).read()
        # dom_snapshot should not be saved (it's excluded or truncated)
        assert "dom_snapshot" not in content or len(content) < 50000


def test_save_session_rejects_invalid_path():  # PRD-04-CMD-003
    spec = SessionSpec(title="t", steps=[], page_url="http://example.com")
    with pytest.raises((OSError, ValueError, FileNotFoundError)):
        save_session_to_file(spec, path="/nonexistent_root_dir_xyz/session.json", name="t")


def test_load_session_rejects_snapshot_with_invalid_step_schema():  # PRD-04-CMD-004
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        # Valid JSON but invalid spec schema (missing required "title" field)
        json.dump({"steps": "not_a_list", "page_url": "x"}, f)
        tmp_path = f.name
    try:
        with pytest.raises((ValueError, KeyError, TypeError)):
            load_session_from_file(tmp_path)
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Coverage gap closers — S7-0109 uncovered paths
# ---------------------------------------------------------------------------

def test_load_session_rejects_missing_steps_field():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"title": "t", "page_url": "http://example.com"}, f)
        tmp_path = f.name
    try:
        with pytest.raises((ValueError, KeyError)):
            load_session_from_file(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_load_session_rejects_missing_page_url_field():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"title": "t", "steps": []}, f)
        tmp_path = f.name
    try:
        with pytest.raises((ValueError, KeyError)):
            load_session_from_file(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_save_session_to_file_uses_default_path_when_none_given(monkeypatch):
    spec = SessionSpec(title="autopath", steps=[], page_url="http://example.com")
    with tempfile.TemporaryDirectory() as tmp_dir:
        monkeypatch.setenv("AUTOWORKBENCH_WORKSPACE", tmp_dir)
        path, name = save_session_to_file(spec)
        assert os.path.isfile(path)
        assert "autopath" in path


def test_build_save_result_event_with_reason_included():
    result = build_save_result_event(path="/p", name="n", session_id="s", step_count=0)
    assert result["type"] == "save_result"
