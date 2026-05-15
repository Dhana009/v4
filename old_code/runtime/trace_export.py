"""
runtime/trace_export.py

Trace export for frontend Trace tab — structured, redacted payload.

Source rule: S6-1107, S6-1108.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from runtime.trace_events import TraceEvent, TraceEventType, TraceRecord
from runtime.redaction_policy import redact_payload


@dataclass
class TraceExportPayload:
    session_id: str
    events: list[dict[str, Any]]
    exported_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TraceFilter:
    event_types: list[TraceEventType] | None = None
    step_ids: list[str] | None = None


def export_trace_for_frontend(record: TraceRecord) -> TraceExportPayload:
    """Serialize and redact trace record for frontend consumption."""
    serialized = []
    for event in record.events:
        redacted_payload = redact_payload(event.payload)
        serialized.append({
            "event_type": event.event_type.value,
            "step_id": event.step_id,
            "payload": redacted_payload,
            "timestamp": event.timestamp,
        })
    return TraceExportPayload(session_id=record.session_id, events=serialized)


def filter_trace_events(
    record: TraceRecord,
    trace_filter: TraceFilter,
) -> list[TraceEvent]:
    events = list(record.events)
    if trace_filter.event_types is not None:
        events = [e for e in events if e.event_type in trace_filter.event_types]
    if trace_filter.step_ids is not None:
        events = [e for e in events if e.step_id in trace_filter.step_ids]
    return events
