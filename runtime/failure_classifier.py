"""
runtime/failure_classifier.py

Failure classification pipeline for recovery handling.

Source rule: S6-0801 — classify failures before recovery.
Deterministic classification first, LLM diagnoser only when needed.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any


class FailureType(enum.Enum):
    ELEMENT_NOT_FOUND = "element_not_found"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    ASSERTION_FAILURE = "assertion_failure"
    NAVIGATION_ERROR = "navigation_error"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


@dataclass
class FailureClassification:
    failure_type: FailureType
    is_recoverable: bool
    confidence: float = 1.0
    details: str | None = None


_ERROR_PATTERNS: list[tuple[str, FailureType]] = [
    ("elementnotfound", FailureType.ELEMENT_NOT_FOUND),
    ("no element", FailureType.ELEMENT_NOT_FOUND),
    ("locator", FailureType.ELEMENT_NOT_FOUND),
    ("timeout", FailureType.TIMEOUT),
    ("timed out", FailureType.TIMEOUT),
    ("networkerror", FailureType.NETWORK_ERROR),
    ("fetch failed", FailureType.NETWORK_ERROR),
    ("net::", FailureType.NETWORK_ERROR),
    ("assertionerror", FailureType.ASSERTION_FAILURE),
    ("expected", FailureType.ASSERTION_FAILURE),
    ("navigationerror", FailureType.NAVIGATION_ERROR),
    ("permission", FailureType.PERMISSION_DENIED),
]

_NON_RECOVERABLE: frozenset[FailureType] = frozenset({
    FailureType.PERMISSION_DENIED,
})


def classify_failure(error: dict[str, Any]) -> FailureClassification:
    """Classify failure from error dict."""
    error_msg = str(error.get("error", "")).lower()

    for pattern, failure_type in _ERROR_PATTERNS:
        if pattern in error_msg:
            return FailureClassification(
                failure_type=failure_type,
                is_recoverable=failure_type not in _NON_RECOVERABLE,
                details=error.get("error"),
            )

    return FailureClassification(
        failure_type=FailureType.UNKNOWN,
        is_recoverable=True,
        confidence=0.3,
    )
