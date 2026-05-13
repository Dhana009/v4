"""
tests/test_error_events.py

Sprint 7 Cluster 2 — S7-0209: fail-closed schema and error events visible to frontend.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_schema_error_event,
    build_provider_error_event,
    build_malformed_output_error_event,
)


# ---------------------------------------------------------------------------
# Unit Tests — schema_error
# ---------------------------------------------------------------------------

def test_schema_error_event_type_correct():  # S7-0209
    result = build_schema_error_event(
        purpose="page_validation_recommender",
        error_type="validation_failure",
        error_message="missing required field",
        retry_count=1,
        max_retries=2,
    )
    assert result["type"] == "schema_error"


def test_schema_error_event_includes_purpose():  # S7-0209
    result = build_schema_error_event(
        purpose="page_validation_recommender",
        error_type="validation_failure",
        error_message="missing required field",
        retry_count=1,
        max_retries=2,
    )
    assert result["purpose"] == "page_validation_recommender"


def test_schema_error_event_includes_retry_count():  # S7-0209
    result = build_schema_error_event(
        purpose="p",
        error_type="e",
        error_message="msg",
        retry_count=2,
        max_retries=3,
    )
    assert result["retry_count"] == 2
    assert result["max_retries"] == 3


def test_schema_error_event_uses_backend_envelope():  # S7-0209
    result = build_schema_error_event(
        purpose="p", error_type="e", error_message="m", retry_count=0, max_retries=1
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_schema_error_event_schema_version():  # GOV-S7-C0-007
    result = build_schema_error_event(
        purpose="p", error_type="e", error_message="m", retry_count=0, max_retries=1
    )
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_schema_error_redacts_sensitive_data():  # GOV-S7-C2
    result = build_schema_error_event(
        purpose="p",
        error_type="e",
        error_message="api key sk-abc123 failed",
        retry_count=0,
        max_retries=1,
    )
    import json
    payload_str = json.dumps(result)
    assert "sk-abc123" not in payload_str


def test_schema_error_no_raw_prompt_dump():  # GOV-S7-C2
    result = build_schema_error_event(
        purpose="p",
        error_type="e",
        error_message="m",
        retry_count=0,
        max_retries=1,
    )
    import json
    payload_str = json.dumps(result)
    assert "OPENAI_API_KEY" not in payload_str


# ---------------------------------------------------------------------------
# Unit Tests — provider_error
# ---------------------------------------------------------------------------

def test_provider_error_event_type_correct():  # S7-0209
    result = build_provider_error_event(
        purpose="journey_planner",
        error_type="timeout",
        error_message="provider timed out",
        retryable=True,
    )
    assert result["type"] == "provider_error"


def test_provider_error_event_includes_retryable():  # S7-0209
    result = build_provider_error_event(
        purpose="p",
        error_type="timeout",
        error_message="m",
        retryable=True,
    )
    assert result["retryable"] is True


def test_provider_error_event_retryable_false():  # S7-0209
    result = build_provider_error_event(
        purpose="p",
        error_type="rate_limit",
        error_message="m",
        retryable=False,
    )
    assert result["retryable"] is False


def test_provider_error_event_uses_backend_envelope():  # S7-0209
    result = build_provider_error_event(
        purpose="p", error_type="e", error_message="m", retryable=False
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_provider_error_redacts_sensitive_data():  # GOV-S7-C2
    result = build_provider_error_event(
        purpose="p",
        error_type="e",
        error_message="sk-secret-key appeared in error",
        retryable=False,
    )
    import json
    payload_str = json.dumps(result)
    assert "sk-secret-key" not in payload_str


# ---------------------------------------------------------------------------
# Unit Tests — malformed_output_error
# ---------------------------------------------------------------------------

def test_malformed_output_error_type_correct():  # S7-0209
    result = build_malformed_output_error_event(
        purpose="step_plan_normalizer",
        error_message="output was not valid JSON",
    )
    assert result["type"] == "malformed_output_error"


def test_malformed_output_error_includes_purpose():  # S7-0209
    result = build_malformed_output_error_event(
        purpose="step_plan_normalizer",
        error_message="not valid JSON",
    )
    assert result["purpose"] == "step_plan_normalizer"


def test_malformed_output_error_safe_sample_truncated():  # GOV-S7-C2
    long_output = "x" * 10000
    result = build_malformed_output_error_event(
        purpose="p",
        error_message="bad output",
        safe_output_sample=long_output,
    )
    import json
    payload_str = json.dumps(result)
    assert len(payload_str) < 50000


def test_malformed_output_error_uses_backend_envelope():  # S7-0209
    result = build_malformed_output_error_event(
        purpose="p",
        error_message="bad output",
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_schema_error_rejects_empty_purpose():  # S7-0209
    with pytest.raises(ValueError, match="purpose"):
        build_schema_error_event(
            purpose="", error_type="e", error_message="m", retry_count=0, max_retries=1
        )


def test_schema_error_rejects_empty_error_type():  # S7-0209
    with pytest.raises(ValueError, match="error_type"):
        build_schema_error_event(
            purpose="p", error_type="", error_message="m", retry_count=0, max_retries=1
        )


def test_schema_error_rejects_negative_retry_count():  # S7-0209
    with pytest.raises(ValueError):
        build_schema_error_event(
            purpose="p", error_type="e", error_message="m", retry_count=-1, max_retries=1
        )


def test_provider_error_rejects_empty_purpose():  # S7-0209
    with pytest.raises(ValueError, match="purpose"):
        build_provider_error_event(purpose="", error_type="e", error_message="m", retryable=False)


def test_provider_error_rejects_empty_error_type():  # S7-0209
    with pytest.raises(ValueError, match="error_type"):
        build_provider_error_event(
            purpose="p", error_type="", error_message="m", retryable=False
        )


def test_malformed_output_error_rejects_empty_purpose():  # S7-0209
    with pytest.raises(ValueError, match="purpose"):
        build_malformed_output_error_event(purpose="", error_message="bad")


def test_malformed_output_error_rejects_empty_message():  # S7-0209
    with pytest.raises(ValueError, match="error_message"):
        build_malformed_output_error_event(purpose="p", error_message="")


# ---------------------------------------------------------------------------
# Fail-closed invariants
# ---------------------------------------------------------------------------

def test_schema_error_does_not_imply_plan_ready():  # S7-0209
    result = build_schema_error_event(
        purpose="p", error_type="e", error_message="m", retry_count=2, max_retries=2
    )
    assert result["type"] != "plan_ready"


def test_provider_error_does_not_imply_step_recorded():  # S7-0209
    result = build_provider_error_event(
        purpose="p", error_type="timeout", error_message="m", retryable=True
    )
    assert result["type"] != "step_recorded"
