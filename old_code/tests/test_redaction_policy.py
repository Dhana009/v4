"""
tests/test_redaction_policy.py

Tests for Cluster 11: Redaction Policy.
S6-1105.
"""
from __future__ import annotations

import pytest
from runtime.redaction_policy import (
    RedactionReport,
    redact_payload,
    is_redacted,
    REDACTED_SENTINEL,
)


def test_redact_password_field():
    payload = {"username": "alice", "password": "secret123"}
    result = redact_payload(payload)
    assert result["username"] == "alice"
    assert result["password"] == REDACTED_SENTINEL


def test_redact_token_field():
    payload = {"token": "eyJhbGci...", "action": "click"}
    result = redact_payload(payload)
    assert result["token"] == REDACTED_SENTINEL
    assert result["action"] == "click"


def test_redact_secret_field():
    payload = {"secret": "my-secret-key", "url": "https://example.com"}
    result = redact_payload(payload)
    assert result["secret"] == REDACTED_SENTINEL


def test_redact_api_key():
    payload = {"api_key": "sk-abc123", "page": "login"}
    result = redact_payload(payload)
    assert result["api_key"] == REDACTED_SENTINEL


def test_safe_fields_not_redacted():
    payload = {"action": "click", "locator": "[data-testid=btn]", "step_id": "s1"}
    result = redact_payload(payload)
    assert result["action"] == "click"
    assert result["locator"] == "[data-testid=btn]"


def test_redaction_report_tracks_redacted_keys():
    payload = {"password": "secret", "email": "user@example.com", "token": "tok123"}
    report = RedactionReport()
    result = redact_payload(payload, report=report)
    assert "password" in report.redacted_keys
    assert "token" in report.redacted_keys
    assert "email" not in report.redacted_keys


def test_is_redacted_sentinel():
    assert is_redacted(REDACTED_SENTINEL)
    assert not is_redacted("normal value")
    assert not is_redacted(None)


def test_nested_redaction():
    payload = {"step": {"action": "fill", "value": {"password": "hunter2"}}}
    result = redact_payload(payload)
    assert result["step"]["value"]["password"] == REDACTED_SENTINEL


def test_no_secrets_survive_redaction():
    payload = {
        "password": "p@ssw0rd",
        "api_key": "sk-123",
        "token": "bearer-xyz",
        "secret": "top-secret",
        "auth": "Basic abc==",
    }
    result = redact_payload(payload)
    for key in payload:
        assert result[key] == REDACTED_SENTINEL
