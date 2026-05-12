"""
runtime/test_data_policy.py

Test data requirement classification, safe proposal, and sensitive data redaction.

Source rule: S6-0705/0706/0707 — test data classified as sensitive/normal.
Safe fake test data proposed (never real credentials). Sensitive data redacted.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any


class TestDataClassification(enum.Enum):
    NORMAL = "normal"
    SENSITIVE = "sensitive"
    SECRET = "secret"


@dataclass
class TestDataRequirement:
    field_name: str
    value: Any


_SENSITIVE_FIELD_NAMES: frozenset[str] = frozenset({
    "password", "passwd", "credit_card", "card_number", "cvv",
    "ssn", "social_security", "api_key", "token", "secret",
    "private_key", "auth_token", "access_token",
})

_REDACT_KEYS: frozenset[str] = frozenset({
    "password", "passwd", "api_key", "apikey", "token", "secret",
    "credential", "credentials", "auth_token", "access_token",
    "private_key", "credit_card", "card_number", "cvv", "ssn",
})

_SAFE_PROPOSALS: dict[str, str] = {
    "username": "test_user_001",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "phone": "555-0100",
    "address": "123 Test Street",
    "city": "Testville",
    "zip": "00000",
    "password": "TestPass123!",
    "credit_card": "4111111111111111",  # test card number
    "cvv": "123",
    "default": "test_value",
}


def classify_test_data(req: TestDataRequirement) -> TestDataClassification:
    """Classify test data requirement as SENSITIVE or NORMAL."""
    field_lower = req.field_name.lower()
    if field_lower in _SENSITIVE_FIELD_NAMES:
        return TestDataClassification.SENSITIVE
    return TestDataClassification.NORMAL


def propose_safe_test_data(req: TestDataRequirement) -> str:
    """Propose safe fake test data for a requirement.

    Returns clearly fake/test values, never real credentials.
    """
    field_lower = req.field_name.lower()
    return _SAFE_PROPOSALS.get(field_lower, _SAFE_PROPOSALS["default"])


def redact_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with sensitive fields redacted."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in _REDACT_KEYS:
            result[key] = "[REDACTED]"
        else:
            result[key] = value
    return result
