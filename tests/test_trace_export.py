"""
tests/test_trace_export.py

Tests for Cluster 11: Trace Export and Frontend Trace Data Contract.
S6-1107, S6-1108.
"""
from __future__ import annotations

import pytest
from runtime.trace_events import TraceWriter, TraceEventType
from runtime.trace_export import (
    TraceExportPayload,
    export_trace_for_frontend,
    filter_trace_events,
    TraceFilter,
)


def test_export_trace_returns_payload():
    writer = TraceWriter(session_id="sess-1")
    writer.emit(TraceEventType.STEP_START, step_id="s1", payload={"action": "click"})
    writer.emit(TraceEventType.LLM_CALL_START, step_id="s1", payload={"purpose": "plan_generation"})
    record = writer.get_record()
    payload = export_trace_for_frontend(record)
    assert isinstance(payload, TraceExportPayload)
    assert payload.session_id == "sess-1"
    assert isinstance(payload.events, list)
    assert len(payload.events) == 2


def test_export_trace_events_are_serializable():
    writer = TraceWriter(session_id="sess-2")
    writer.emit(TraceEventType.FAILURE, step_id="s1", payload={"error": "TimeoutError"})
    record = writer.get_record()
    payload = export_trace_for_frontend(record)
    # Each event must be a dict-like serializable structure
    for event in payload.events:
        assert "event_type" in event
        assert "timestamp" in event


def test_filter_trace_events_by_type():
    writer = TraceWriter(session_id="sess-3")
    writer.emit(TraceEventType.STEP_START, step_id="s1", payload={})
    writer.emit(TraceEventType.LLM_CALL_START, step_id="s1", payload={})
    writer.emit(TraceEventType.FAILURE, step_id="s1", payload={})
    record = writer.get_record()

    filtered = filter_trace_events(record, TraceFilter(event_types=[TraceEventType.FAILURE]))
    assert len(filtered) == 1
    assert filtered[0].event_type == TraceEventType.FAILURE


def test_filter_trace_events_by_step():
    writer = TraceWriter(session_id="sess-4")
    writer.emit(TraceEventType.STEP_START, step_id="s1", payload={})
    writer.emit(TraceEventType.STEP_START, step_id="s2", payload={})
    record = writer.get_record()

    filtered = filter_trace_events(record, TraceFilter(step_ids=["s1"]))
    assert all(e.step_id == "s1" for e in filtered)


def test_export_contains_no_secrets():
    writer = TraceWriter(session_id="sess-5")
    writer.emit(
        TraceEventType.LLM_CALL_START,
        step_id="s1",
        payload={"password": "secret123", "purpose": "plan_generation"},
    )
    record = writer.get_record()
    payload = export_trace_for_frontend(record)
    export_str = str(payload.events)
    assert "secret123" not in export_str


def test_trace_export_payload_has_metadata():
    writer = TraceWriter(session_id="sess-6")
    record = writer.get_record()
    payload = export_trace_for_frontend(record)
    assert hasattr(payload, "session_id")
    assert hasattr(payload, "events")
    assert hasattr(payload, "exported_at")
