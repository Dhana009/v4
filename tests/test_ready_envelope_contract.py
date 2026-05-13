"""
tests/test_ready_envelope_contract.py

Sprint 7 Cluster 1 — S7-0105: typed ready/browser_ready envelope contract tests.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_browser_ready_event,
    build_typed_ready_envelope,
)


# ---------------------------------------------------------------------------
# Unit Tests — ready envelope
# ---------------------------------------------------------------------------

def test_build_typed_ready_envelope_includes_session_id():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="sess-1", workspace="/ws", mode="llm", url="http://localhost")
    assert result["session_id"] == "sess-1"


def test_build_typed_ready_envelope_includes_workspace():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="sess-1", workspace="/workspace", mode="llm", url="http://localhost")
    assert result["workspace"] == "/workspace"


def test_build_typed_ready_envelope_includes_mode():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="sess-1", workspace="/ws", mode="manual", url="http://localhost")
    assert result["mode"] == "manual"


def test_build_typed_ready_envelope_includes_url():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="sess-1", workspace="/ws", mode="llm", url="http://example.com")
    assert result["url"] == "http://example.com"


def test_build_typed_ready_envelope_includes_backend_ready_flag():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="sess-1", workspace="/ws", mode="llm", url="http://localhost", backend_ready=True)
    assert result["backend_ready"] is True


def test_build_typed_ready_envelope_includes_browser_ready_flag():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="sess-1", workspace="/ws", mode="llm", url="http://localhost", browser_ready=False)
    assert result["browser_ready"] is False


def test_build_typed_ready_envelope_includes_session_active_flag():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="sess-1", workspace="/ws", mode="llm", url="http://localhost", session_active=True)
    assert result["session_active"] is True


def test_build_typed_ready_envelope_defaults():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="sess-1", workspace="/ws", mode="llm", url="http://localhost")
    # defaults: backend_ready=True, browser_ready=False, session_active=False
    assert result["backend_ready"] is True
    assert result["browser_ready"] is False
    assert result["session_active"] is False


# ---------------------------------------------------------------------------
# Unit Tests — browser_ready event
# ---------------------------------------------------------------------------

def test_build_browser_ready_event_includes_browser_ready_flag():  # PRD-04-BE-007
    result = build_browser_ready_event(browser_ready=True)
    assert result["browser_ready"] is True


def test_build_browser_ready_event_includes_context_and_url():  # PRD-04-BE-007
    result = build_browser_ready_event(browser_ready=True, context="chromium", url="http://localhost:3000")
    assert result.get("context") == "chromium"
    assert result.get("url") == "http://localhost:3000"


def test_build_browser_ready_event_optional_context_absent_when_not_given():  # PRD-04-BE-007
    result = build_browser_ready_event(browser_ready=True)
    assert result.get("context") is None or "context" not in result


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------

def test_ready_event_type_field_is_ready():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="s", workspace="/w", mode="llm", url="u")
    assert result["type"] == "ready"


def test_browser_ready_event_type_field_is_browser_ready():  # PRD-04-BE-007
    result = build_browser_ready_event(browser_ready=True)
    assert result["type"] == "browser_ready"


def test_ready_envelope_uses_backend_event_envelope():  # PRD-04-BE-007
    result = build_typed_ready_envelope(session_id="s", workspace="/w", mode="llm", url="u")
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_browser_ready_uses_backend_event_envelope():  # PRD-04-BE-007
    result = build_browser_ready_event(browser_ready=True)
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_typed_ready_emitted_on_connection():  # PRD-03-FE-002
    # Builder produces a valid ready event — emission seam in server.py
    result = build_typed_ready_envelope(session_id="sess-new", workspace="/ws", mode="llm", url="http://localhost")
    assert result["type"] == "ready"
    assert result["session_id"] == "sess-new"


def test_browser_ready_emitted_after_browser_launch():  # PRD-04-BE-007
    # Builder can be called with browser_ready=True after launch
    result = build_browser_ready_event(browser_ready=True, url="http://localhost:3000")
    assert result["browser_ready"] is True


# ---------------------------------------------------------------------------
# Negative Tests (required by GOV-S7-C0-009)
# ---------------------------------------------------------------------------

def test_ready_envelope_rejects_empty_session_id():  # PRD-04-BE-007
    with pytest.raises(ValueError, match="session_id"):
        build_typed_ready_envelope(session_id="", workspace="/ws", mode="llm", url="http://localhost")


def test_build_ready_envelope_with_false_backend_ready_is_valid():  # PRD-04-BE-007
    # backend_ready=False is a valid signal (backend not yet fully up)
    result = build_typed_ready_envelope(session_id="s", workspace="/w", mode="llm", url="u", backend_ready=False)
    assert result["backend_ready"] is False
    assert result["type"] == "ready"


def test_ready_envelope_rejects_whitespace_session_id():  # PRD-04-BE-007
    with pytest.raises(ValueError, match="session_id"):
        build_typed_ready_envelope(session_id="   ", workspace="/ws", mode="llm", url="http://localhost")
