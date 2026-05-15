"""
runtime/redaction.py — Pure deterministic redaction utility (P0 item 22).

Scrubs sensitive keys from structured payloads and redacts inline patterns
(email, JWT, AWS access keys, credit-card numbers, generic hex tokens) from
free-form text before any data is forwarded to the LLM.

Stdlib only. No I/O. No logging. Inputs are never mutated.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

# ---------------------------------------------------------------------------
# Sentinel replacement value
# ---------------------------------------------------------------------------
_REDACTED = "<REDACTED>"

# ---------------------------------------------------------------------------
# Canonical set of sensitive key substrings (case-insensitive matching)
# ---------------------------------------------------------------------------
SENSITIVE_KEYS: tuple[str, ...] = (
    "password",
    "secret",
    "api_key",
    "token",
    "bearer",
    "authorization",
    "cookie",
    "ssn",
    "credit_card",
    "cc_number",
    "cvv",
    "private_key",
    "access_token",
    "refresh_token",
)

# ---------------------------------------------------------------------------
# Compiled regex patterns for redact_text
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    re.ASCII,
)

# JWT: three base64url segments starting with eyJ
_JWT_RE = re.compile(
    r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
)

# AWS access-key ID
_AWS_KEY_RE = re.compile(
    r"AKIA[0-9A-Z]{16}",
)

# Credit-card numbers: 13–19 digits optionally separated by spaces/dashes
_CREDIT_CARD_RE = re.compile(
    r"\b(?:\d[ \-]*?){13,19}\b",
)

# Generic 32+ character hex token (lowercase or uppercase)
_HEX_TOKEN_RE = re.compile(
    r"\b[0-9A-Fa-f]{32,}\b",
)

# Ordered list so more-specific patterns are tried first
_TEXT_PATTERNS: list[re.Pattern[str]] = [
    _JWT_RE,
    _AWS_KEY_RE,
    _HEX_TOKEN_RE,
    _CREDIT_CARD_RE,
    _EMAIL_RE,
]


# ---------------------------------------------------------------------------
# Redactor
# ---------------------------------------------------------------------------
class Redactor:
    """Recursively redact sensitive data from structured objects and free text."""

    def __init__(self, extra_keys: tuple[str, ...] = ()) -> None:
        self._sensitive: tuple[str, ...] = SENSITIVE_KEYS + tuple(
            k.lower() for k in extra_keys
        )
        self._count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def redact(self, obj: Any) -> Any:
        """Return a deep copy of *obj* with sensitive values replaced.

        Walks dicts, lists, and tuples recursively. Dict keys are checked
        case-insensitively for any sensitive substring; matching values are
        replaced with ``"<REDACTED>"``. Non-dict leaf values are returned as-is
        (strings are *not* pattern-scanned here — use ``redact_text`` for that).
        """
        return self._walk(obj)

    def redact_text(self, text: str) -> str:
        """Regex-redact inline sensitive patterns from a plain string."""
        result = text
        for pattern in _TEXT_PATTERNS:
            result = pattern.sub(_REDACTED, result)
        # Count each substitution as one redaction event (compare lengths as proxy)
        if result != text:
            # Count actual number of replacements by re-running on original
            for pattern in _TEXT_PATTERNS:
                matches = pattern.findall(text)
                self._count += len(matches)
        return result

    @property
    def count_redactions(self) -> int:
        """Total number of redactions performed since this instance was created."""
        return self._count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_sensitive_key(self, key: Any) -> bool:
        if not isinstance(key, str):
            return False
        key_lower = key.lower()
        return any(s in key_lower for s in self._sensitive)

    def _walk(self, obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return self._walk_mapping(obj)
        if isinstance(obj, (list, tuple)):
            return self._walk_sequence(obj)
        # Scalar — return as-is (deep copy for safety)
        return copy.copy(obj) if not isinstance(obj, (str, int, float, bool, type(None))) else obj

    def _walk_mapping(self, obj: Mapping[Any, Any]) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        for key, value in obj.items():
            if self._is_sensitive_key(key):
                result[key] = _REDACTED
                self._count += 1
            else:
                result[key] = self._walk(value)
        return result

    def _walk_sequence(self, obj: Any) -> Any:
        walked = [self._walk(item) for item in obj]
        if isinstance(obj, tuple):
            return tuple(walked)
        return walked


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

def redact_payload(
    payload: Any,
    extra_keys: tuple[str, ...] = (),
) -> Any:
    """Construct a one-shot :class:`Redactor` and return the redacted payload."""
    return Redactor(extra_keys=extra_keys).redact(payload)
