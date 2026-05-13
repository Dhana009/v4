"""
tests/test_page_analysis_events.py

Sprint 7 Cluster 2 — S7-0203: page_analysis_started and page_summary_ready events.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_page_analysis_started_event,
    build_page_summary_ready_event,
    build_page_analysis_failed_event,
)


# ---------------------------------------------------------------------------
# Unit Tests — page_analysis_started
# ---------------------------------------------------------------------------

def test_page_analysis_started_includes_request_id():  # S7-0203
    result = build_page_analysis_started_event(
        request_id="req-1", page_url="http://example.com"
    )
    assert result["request_id"] == "req-1"


def test_page_analysis_started_includes_page_url():  # S7-0203
    result = build_page_analysis_started_event(
        request_id="req-1", page_url="http://example.com"
    )
    assert result["page_url"] == "http://example.com"


def test_page_analysis_started_type_correct():  # S7-0203
    result = build_page_analysis_started_event(
        request_id="req-1", page_url="http://example.com"
    )
    assert result["type"] == "page_analysis_started"


def test_page_analysis_started_includes_analysis_type():  # S7-0203
    result = build_page_analysis_started_event(
        request_id="req-1", page_url="http://example.com", analysis_type="live_invocation"
    )
    assert result["analysis_type"] == "live_invocation"


def test_page_analysis_started_default_analysis_type_is_fallback():  # S7-0203
    result = build_page_analysis_started_event(
        request_id="req-1", page_url="http://example.com"
    )
    assert result["analysis_type"] in {"live_invocation", "cached", "fallback"}


def test_page_analysis_started_uses_backend_envelope():  # S7-0203
    result = build_page_analysis_started_event(
        request_id="req-1", page_url="http://example.com"
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Unit Tests — page_summary_ready
# ---------------------------------------------------------------------------

def test_page_summary_ready_includes_request_id():  # S7-0203
    result = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "Test page", "sections": []},
    )
    assert result["request_id"] == "req-1"


def test_page_summary_ready_includes_page_summary():  # S7-0203
    result = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "Login page", "sections": ["login"]},
    )
    assert result["page_summary"]["page_summary"] == "Login page"


def test_page_summary_ready_type_correct():  # S7-0203
    result = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "p"},
    )
    assert result["type"] == "page_summary_ready"


def test_page_summary_ready_includes_timestamp():  # S7-0203
    result = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "p"},
    )
    assert "timestamp" in result or "emitted_at" in result


def test_page_summary_ready_no_raw_html_in_payload():  # GOV-S7-C2
    result = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "p", "raw_html": "<html/>"},
    )
    import json
    payload_str = json.dumps(result)
    assert "raw_html" not in payload_str


def test_page_summary_ready_uses_backend_envelope():  # S7-0203
    result = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "p"},
    )
    assert "schema_version" in result
    assert "payload" in result


# ---------------------------------------------------------------------------
# Unit Tests — page_analysis_failed
# ---------------------------------------------------------------------------

def test_page_analysis_failed_type_correct():  # S7-0203
    result = build_page_analysis_failed_event(
        request_id="req-1", page_url="http://example.com", reason="timeout"
    )
    assert result["type"] == "page_analysis_failed"


def test_page_analysis_failed_includes_reason():  # S7-0203
    result = build_page_analysis_failed_event(
        request_id="req-1", page_url="http://example.com", reason="provider_error"
    )
    assert "provider_error" in result["reason"]


def test_page_analysis_failed_includes_request_id():  # S7-0203
    result = build_page_analysis_failed_event(
        request_id="req-abc", page_url="http://example.com", reason="timeout"
    )
    assert result["request_id"] == "req-abc"


def test_page_analysis_failed_uses_backend_envelope():  # S7-0203
    result = build_page_analysis_failed_event(
        request_id="req-1", page_url="http://example.com", reason="timeout"
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Contract Tests — payload shape
# ---------------------------------------------------------------------------

def test_page_analysis_started_schema_version():  # GOV-S7-C0-007
    result = build_page_analysis_started_event(
        request_id="req-1", page_url="http://example.com"
    )
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_page_summary_ready_schema_version():  # GOV-S7-C0-007
    result = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "p"},
    )
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_page_analysis_started_rejects_empty_request_id():  # S7-0203
    with pytest.raises(ValueError, match="request_id"):
        build_page_analysis_started_event(request_id="", page_url="http://example.com")


def test_page_analysis_started_rejects_empty_page_url():  # S7-0203
    with pytest.raises(ValueError, match="page_url"):
        build_page_analysis_started_event(request_id="req-1", page_url="")


def test_page_summary_ready_rejects_empty_request_id():  # S7-0203
    with pytest.raises(ValueError, match="request_id"):
        build_page_summary_ready_event(request_id="", page_summary={"page_summary": "p"})


def test_page_summary_ready_rejects_none_page_summary():  # S7-0203
    with pytest.raises((ValueError, TypeError)):
        build_page_summary_ready_event(request_id="req-1", page_summary=None)  # type: ignore


def test_page_analysis_failed_rejects_empty_reason():  # S7-0203
    with pytest.raises(ValueError, match="reason"):
        build_page_analysis_failed_event(
            request_id="req-1", page_url="http://example.com", reason=""
        )


def test_page_analysis_failed_rejects_empty_request_id():  # S7-0203
    with pytest.raises(ValueError, match="request_id"):
        build_page_analysis_failed_event(
            request_id="", page_url="http://example.com", reason="timeout"
        )
