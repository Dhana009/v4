"""
tests/test_trace_events.py

Tests for Cluster 11: Trace Events + Artifacts + Observability.
S6-1101, S6-1102, S6-1103.
"""
from __future__ import annotations

import pytest
from runtime.trace_events import (
    TraceEventType,
    TraceEvent,
    TraceRecord,
    make_trace_event,
    TraceWriter,
)


# ---------------------------------------------------------------------------
# S6-1101: Structured trace event model
# ---------------------------------------------------------------------------

def test_trace_event_has_required_fields():
    event = make_trace_event(
        event_type=TraceEventType.LLM_CALL_START,
        step_id="s1",
        payload={"purpose": "plan_generation"},
    )
    assert isinstance(event, TraceEvent)
    assert event.event_type == TraceEventType.LLM_CALL_START
    assert event.step_id == "s1"
    assert event.payload is not None
    assert event.timestamp is not None


def test_trace_event_types_cover_lifecycle():
    required = [
        TraceEventType.LLM_CALL_START,
        TraceEventType.LLM_CALL_END,
        TraceEventType.STEP_START,
        TraceEventType.STEP_END,
        TraceEventType.FAILURE,
        TraceEventType.RECOVERY_START,
        TraceEventType.RECOVERY_END,
        TraceEventType.PERMISSION_CHECK,
        TraceEventType.LOCATOR_DECISION,
        TraceEventType.ARTIFACT_WRITTEN,
    ]
    for t in required:
        assert isinstance(t, TraceEventType)


def test_trace_record_holds_events():
    writer = TraceWriter(session_id="sess-1")
    writer.emit(TraceEventType.STEP_START, step_id="s1", payload={})
    writer.emit(TraceEventType.STEP_END, step_id="s1", payload={"success": True})
    record = writer.get_record()
    assert isinstance(record, TraceRecord)
    assert len(record.events) == 2


def test_trace_cannot_mutate_runtime_truth():
    """Trace is read-only mirror — no state-mutation methods on TraceRecord."""
    record = TraceRecord(session_id="s", events=[])
    assert not hasattr(record, "set_status")
    assert not hasattr(record, "update_state")
    assert not hasattr(record, "resolve")


# ---------------------------------------------------------------------------
# S6-1102: Backend lifecycle event emission
# ---------------------------------------------------------------------------

def test_writer_emit_step_events():
    writer = TraceWriter(session_id="sess-2")
    writer.emit(TraceEventType.STEP_START, step_id="s1", payload={"action": "click"})
    writer.emit(TraceEventType.FAILURE, step_id="s1", payload={"error": "ElementNotFoundError"})
    record = writer.get_record()
    types = [e.event_type for e in record.events]
    assert TraceEventType.STEP_START in types
    assert TraceEventType.FAILURE in types


def test_writer_emit_permission_check():
    writer = TraceWriter(session_id="sess-3")
    writer.emit(TraceEventType.PERMISSION_CHECK, step_id="s1", payload={"risk": "HIGH", "allowed": False})
    record = writer.get_record()
    assert any(e.event_type == TraceEventType.PERMISSION_CHECK for e in record.events)


# ---------------------------------------------------------------------------
# S6-1103: LLM call artifact
# ---------------------------------------------------------------------------

def test_writer_emit_llm_call():
    writer = TraceWriter(session_id="sess-4")
    writer.emit(
        TraceEventType.LLM_CALL_START,
        step_id="s1",
        payload={"purpose": "plan_generation", "token_estimate": 1200},
    )
    writer.emit(
        TraceEventType.LLM_CALL_END,
        step_id="s1",
        payload={"purpose": "plan_generation", "success": True, "tokens_used": 980},
    )
    record = writer.get_record()
    llm_events = [e for e in record.events if "llm" in e.event_type.value]
    assert len(llm_events) == 2
