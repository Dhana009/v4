"""
tests/test_token_report_event.py

Sprint 7 Cluster 2 — S7-0207: token/telemetry event payloads for UI.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_token_report_event,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_token_report_event_type_correct():  # S7-0207
    result = build_token_report_event(
        purpose="journey_planner",
        model_class="main",
        input_tokens=1000,
        output_tokens=200,
    )
    assert result["type"] == "token_report"


def test_token_report_event_includes_purpose():  # S7-0207
    result = build_token_report_event(
        purpose="journey_planner",
        model_class="main",
        input_tokens=1000,
        output_tokens=200,
    )
    assert result["purpose"] == "journey_planner"


def test_token_report_event_includes_model_class():  # S7-0207
    result = build_token_report_event(
        purpose="page_intelligence_summarizer",
        model_class="cheap",
        input_tokens=500,
        output_tokens=100,
    )
    assert result["model_class"] == "cheap"


def test_token_report_event_includes_input_tokens():  # S7-0207
    result = build_token_report_event(
        purpose="p",
        model_class="m",
        input_tokens=1234,
        output_tokens=56,
    )
    assert result["input_tokens"] == 1234


def test_token_report_event_includes_output_tokens():  # S7-0207
    result = build_token_report_event(
        purpose="p",
        model_class="m",
        input_tokens=1000,
        output_tokens=300,
    )
    assert result["output_tokens"] == 300


def test_token_report_event_uses_backend_envelope():  # S7-0207
    result = build_token_report_event(
        purpose="p", model_class="m", input_tokens=100, output_tokens=50
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_token_report_event_schema_version():  # GOV-S7-C0-007
    result = build_token_report_event(
        purpose="p", model_class="m", input_tokens=100, output_tokens=50
    )
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_token_report_event_includes_optional_call_id():  # S7-0207
    result = build_token_report_event(
        purpose="p",
        model_class="m",
        input_tokens=100,
        output_tokens=50,
        call_id="call-123",
    )
    assert result.get("call_id") == "call-123"


def test_token_report_event_includes_cached_tokens_when_given():  # S7-0207
    result = build_token_report_event(
        purpose="p",
        model_class="m",
        input_tokens=1000,
        output_tokens=100,
        cached_tokens=400,
    )
    assert result.get("cached_tokens") == 400


def test_token_report_event_includes_latency_ms_when_given():  # S7-0207
    result = build_token_report_event(
        purpose="p",
        model_class="m",
        input_tokens=100,
        output_tokens=50,
        latency_ms=320,
    )
    assert result.get("latency_ms") == 320


def test_token_report_missing_tokens_safe():  # S7-0207
    result = build_token_report_event(
        purpose="p",
        model_class="m",
        input_tokens=0,
        output_tokens=0,
    )
    assert result["input_tokens"] == 0
    assert result["output_tokens"] == 0


# ---------------------------------------------------------------------------
# Security / redaction Contract Tests
# ---------------------------------------------------------------------------

def test_token_report_does_not_include_api_key():  # GOV-S7-C2
    import json
    result = build_token_report_event(
        purpose="p", model_class="m", input_tokens=100, output_tokens=50
    )
    payload_str = json.dumps(result)
    assert "sk-" not in payload_str
    assert "OPENAI_API_KEY" not in payload_str


def test_token_report_does_not_include_prompt_content():  # GOV-S7-C2
    result = build_token_report_event(
        purpose="p", model_class="m", input_tokens=100, output_tokens=50
    )
    assert "messages" not in result
    assert "system_prompt" not in result


def test_token_report_estimated_cost_optional():  # S7-0207
    result = build_token_report_event(
        purpose="p",
        model_class="m",
        input_tokens=1000,
        output_tokens=200,
        estimated_cost=0.005,
    )
    assert result.get("estimated_cost") == pytest.approx(0.005, rel=1e-3)


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_token_report_rejects_empty_purpose():  # S7-0207
    with pytest.raises(ValueError, match="purpose"):
        build_token_report_event(purpose="", model_class="m", input_tokens=100, output_tokens=50)


def test_token_report_rejects_empty_model_class():  # S7-0207
    with pytest.raises(ValueError, match="model_class"):
        build_token_report_event(purpose="p", model_class="", input_tokens=100, output_tokens=50)


def test_token_report_rejects_negative_input_tokens():  # S7-0207
    with pytest.raises(ValueError):
        build_token_report_event(purpose="p", model_class="m", input_tokens=-1, output_tokens=50)


def test_token_report_rejects_negative_output_tokens():  # S7-0207
    with pytest.raises(ValueError):
        build_token_report_event(purpose="p", model_class="m", input_tokens=100, output_tokens=-1)
