"""
tests/test_page_intelligence_live_invocation.py

Sprint 7 Cluster 2 — S7-0201: Page Intelligence live invocation boundary.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.page_intelligence_live import (
    invoke_page_intelligence,
    needs_page_intelligence,
    PageIntelligencePacketResult,
)
from runtime.event_contracts import (
    build_page_analysis_started_event,
    build_page_summary_ready_event,
    build_page_analysis_failed_event,
)


# ---------------------------------------------------------------------------
# Unit Tests — boundary detection
# ---------------------------------------------------------------------------

def test_needs_pi_returns_true_for_weak_dom():  # S7-0201
    assert needs_page_intelligence({"dom_strength": "weak"}) is True


def test_needs_pi_returns_true_for_unknown_dom():  # S7-0201
    assert needs_page_intelligence({"dom_strength": "unknown"}) is True


def test_needs_pi_returns_false_for_strong_dom():  # S7-0201
    assert needs_page_intelligence({"dom_strength": "strong"}) is False


def test_needs_pi_returns_true_when_dom_strength_missing():  # S7-0201
    assert needs_page_intelligence({}) is True


def test_needs_pi_returns_true_for_minimal_dom():  # S7-0201
    assert needs_page_intelligence({"dom_strength": "minimal"}) is True


# ---------------------------------------------------------------------------
# Unit Tests — invocation result
# ---------------------------------------------------------------------------

def test_invoke_returns_packet_result():  # S7-0201
    result = invoke_page_intelligence("http://example.com", None)
    assert isinstance(result, PageIntelligencePacketResult)


def test_invoke_result_has_packet():  # S7-0201
    result = invoke_page_intelligence("http://example.com", None)
    assert isinstance(result.packet, dict)


def test_invoke_result_has_token_estimate():  # S7-0201
    result = invoke_page_intelligence("http://example.com", None)
    assert isinstance(result.token_estimate, int)
    assert result.token_estimate >= 0


def test_invoke_result_has_source():  # S7-0201
    result = invoke_page_intelligence("http://example.com", None)
    assert result.source in {"deterministic", "cheap_model", "fake", "mixed", "fallback"}


def test_invoke_result_no_raw_html_in_packet():  # GOV-S7-C2
    result = invoke_page_intelligence("http://example.com", None)
    import json
    packet_str = json.dumps(result.packet)
    assert "<html" not in packet_str
    assert "raw_html" not in packet_str


def test_invoke_fake_path_labeled_fake():  # S7-0201
    result = invoke_page_intelligence("http://example.com", None)
    # Fake path must be labeled as fake, not live
    assert result.source in {"fake", "deterministic", "fallback"}


def test_invoke_token_estimate_within_limit():  # S7-0201
    result = invoke_page_intelligence("http://example.com", None)
    assert result.token_estimate <= 1500


def test_invoke_fallback_for_blank_url():  # S7-0201
    result = invoke_page_intelligence("about:blank", None)
    assert result.source in {"fallback", "deterministic"}


def test_invoke_fallback_for_empty_url():  # S7-0201
    result = invoke_page_intelligence("", None)
    assert isinstance(result, PageIntelligencePacketResult)


# ---------------------------------------------------------------------------
# Contract Tests — event pipeline (S7-0201 + S7-0203)
# ---------------------------------------------------------------------------

def test_page_analysis_started_event_before_summary():  # S7-0201 + S7-0203
    started = build_page_analysis_started_event(
        request_id="req-1", page_url="http://example.com"
    )
    summary = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "Test", "sections": []},
    )
    assert started["type"] == "page_analysis_started"
    assert summary["type"] == "page_summary_ready"
    assert started["request_id"] == summary["request_id"]


def test_page_analysis_failed_event_on_error():  # S7-0201
    failed = build_page_analysis_failed_event(
        request_id="req-1",
        page_url="http://example.com",
        reason="provider_timeout",
    )
    assert failed["type"] == "page_analysis_failed"
    assert failed["request_id"] == "req-1"


def test_page_analysis_source_in_summary_payload():  # S7-0201
    result = invoke_page_intelligence("http://example.com", None)
    # Source field must be carried to event payload for frontend to distinguish live/fake
    summary_event = build_page_summary_ready_event(
        request_id="req-1",
        page_summary=result.packet,
        source=result.source,
    )
    assert summary_event["type"] == "page_summary_ready"
    # Source may be nested in payload or top-level
    has_source = (
        summary_event.get("source") is not None
        or summary_event.get("payload", {}).get("source") is not None
    )
    assert has_source


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_invoke_pi_does_not_raise_on_none_section():  # S7-0201
    result = invoke_page_intelligence("http://example.com", None)
    assert result is not None


def test_invoke_pi_does_not_execute_browser_action():  # GOV-S7-C2
    # Page Intelligence result is advisory — it must not trigger step execution
    result = invoke_page_intelligence("http://example.com", "main")
    # The result type must be PageIntelligencePacketResult, not a step/action
    assert isinstance(result, PageIntelligencePacketResult)
    assert result.source != "executed"


def test_page_summary_ready_does_not_imply_step_recorded():  # S7-0201
    summary = build_page_summary_ready_event(
        request_id="req-1",
        page_summary={"page_summary": "p"},
    )
    assert summary["type"] != "step_recorded"
