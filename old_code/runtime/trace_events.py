"""
runtime/trace_events.py

Structured trace event model and writer.

Source rule: S6-1101, S6-1102, S6-1103.
Trace mirrors backend events — does NOT mutate runtime truth.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class TraceEventType(enum.Enum):
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    STEP_START = "step_start"
    STEP_END = "step_end"
    FAILURE = "failure"
    RECOVERY_START = "recovery_start"
    RECOVERY_END = "recovery_end"
    PERMISSION_CHECK = "permission_check"
    LOCATOR_DECISION = "locator_decision"
    ARTIFACT_WRITTEN = "artifact_written"
    PRECONDITION_CHECK = "precondition_check"
    CONTEXT_ESCALATION = "context_escalation"
    TOKEN_BUDGET_CHECK = "token_budget_check"


@dataclass(frozen=True)
class TraceEvent:
    event_type: TraceEventType
    step_id: str | None
    payload: dict[str, Any]
    timestamp: str


@dataclass(frozen=True)
class TraceRecord:
    """Immutable snapshot of all trace events — read-only mirror."""
    session_id: str
    events: list[TraceEvent]


def make_trace_event(
    event_type: TraceEventType,
    step_id: str | None,
    payload: dict[str, Any],
) -> TraceEvent:
    return TraceEvent(
        event_type=event_type,
        step_id=step_id,
        payload=payload,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


class TraceWriter:
    """Accumulates trace events; produces immutable TraceRecord on demand."""

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._events: list[TraceEvent] = []

    def emit(
        self,
        event_type: TraceEventType,
        step_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._events.append(make_trace_event(event_type, step_id, payload or {}))

    def get_record(self) -> TraceRecord:
        return TraceRecord(session_id=self._session_id, events=list(self._events))
