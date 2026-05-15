"""
runtime/redaction_policy.py

Redaction policy — no secrets survive artifact or trace writes.

Source rule: S6-1105.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REDACTED_SENTINEL = "[REDACTED]"

_SECRET_KEYS: frozenset[str] = frozenset({
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token", "id_token",
    "secret", "api_key", "apikey", "api_secret",
    "auth", "authorization", "bearer",
    "private_key", "private_secret",
    "credit_card", "ssn", "cvv",
})


@dataclass
class RedactionReport:
    redacted_keys: list[str] = field(default_factory=list)
    total_redacted: int = 0

    def record(self, key: str) -> None:
        self.redacted_keys.append(key)
        self.total_redacted += 1


def _should_redact(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in _SECRET_KEYS or any(s in normalized for s in _SECRET_KEYS)


def redact_payload(
    payload: Any,
    report: RedactionReport | None = None,
    _parent_key: str = "",
) -> Any:
    if isinstance(payload, dict):
        result = {}
        for k, v in payload.items():
            if _should_redact(k):
                result[k] = REDACTED_SENTINEL
                if report is not None:
                    report.record(k)
            else:
                result[k] = redact_payload(v, report=report, _parent_key=k)
        return result
    if isinstance(payload, list):
        return [redact_payload(item, report=report) for item in payload]
    return payload


def is_redacted(value: Any) -> bool:
    return value == REDACTED_SENTINEL
