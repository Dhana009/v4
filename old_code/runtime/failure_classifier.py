"""
runtime/failure_classifier.py

Failure classification pipeline for recovery handling.

Source rule: S6-0801 — classify failures before recovery.
Deterministic classification first, LLM diagnoser only when needed.

Controller integration (runtime_policy §15):
  classify_failure_via_controller() is the preferred call path so that any
  future LLM escalation for unknown failures is mediated by
  LLMRuntimeController (schema-retry + _validate_response).  The current
  implementation is fully deterministic, so the controller call uses
  deterministic_safe=True — no model is invoked.
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


def classify_failure_via_controller(
    error: dict[str, Any],
    *,
    controller: Any | None = None,
) -> FailureClassification:
    """Classify failure, routing telemetry through LLMRuntimeController.

    The classification itself is deterministic (no LLM call).  Passing it
    through the controller ensures schema-retry and _validate_response are
    applied for any future LLM escalation path per runtime_policy §15.

    Parameters
    ----------
    error:
        Error dict with at least an ``"error"`` key containing the error string.
    controller:
        An LLMRuntimeController instance.  If None the function falls back
        to ``classify_failure`` directly (no telemetry emitted).
    """
    classification = classify_failure(error)

    if controller is not None:
        _call = getattr(controller, "call", None)
        if callable(_call):
            import asyncio
            error_summary = str(error.get("error", ""))[:120]
            _coro = _call(
                purpose="failure_classifier",
                messages=[{"role": "user", "content": error_summary}],
                deterministic_safe=True,
                deterministic_reason=f"pattern_match:{classification.failure_type.value}",
            )
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_coro)
                else:
                    loop.run_until_complete(_coro)
            except Exception:  # noqa: BLE001
                pass  # telemetry errors must never break classification

    return classification
