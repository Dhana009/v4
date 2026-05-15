# S7-0901 — Trace Tab Live Timeline

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** [S7-0902, S7-0903]
**Blocked by:** [S7-0500 (frontend event store)]

---

## Objective

Build Trace tab component to render backend `trace_event` timeline in real time. Display event type, timestamp, phase, run_id, step_id, status, reason, correlation id, and source/layer. Show empty state before any events. Reject malformed trace entries with diagnostics. No static demo trace in live mode.

After S7-0901:
- Trace tab component exists and renders traceEntries from frontend event store
- `trace_event` backend events update frontend store
- Timeline renders in chronological order
- Unknown event types show diagnostic row
- No static demo content appears

---

## Source Rules

- PRD-06-TRACE-001: Trace event timeline structure and field display
- PRD-04-BACKEND-010: trace_event payload format and semantics
- PRD-03-FE-C9-001: Trace is evidence only; not runtime truth
- PRD-03-FE-011: No demo/static content in live mode
- GOV-S7-C0-007: No source rule → no test; no test → no implementation

---

## Current Known Context

### What exists
- `trace_events.py` in backend creates trace events
- `trace_export.py` exports trace bundles
- Frontend event store infrastructure (S7-0500) exists but handlers for `trace_event` not yet implemented
- No Trace tab component exists

### What gaps exist
- No Trace tab component
- No `trace_event` event handler in frontend store
- No timeline rendering
- No unknown event type handling
- No empty state

### Current test status
- `tests/test_frontend_llm_mode_complete.py` has contract tests for trace_event schema but no component tests
- No frontend reducer/component tests for Trace tab

---

## Tests First

### Unit Tests

```python
test_trace_event_from_backend_payload()  # PRD-04-BACKEND-010
test_trace_event_timestamp_formatting()  # PRD-06-TRACE-001
test_trace_event_rejects_missing_type()  # GOV-S7-C0-009
test_trace_event_rejects_missing_timestamp()  # GOV-S7-C0-009
```

### Reducer Tests

```python
test_reducer_trace_event_appends_to_timeline()  # PRD-03-FE-C9-001
test_reducer_trace_events_maintain_chronological_order()  # PRD-06-TRACE-001
test_reducer_unknown_event_type_creates_diagnostic_row()  # PRD-06-TRACE-001
test_reducer_ignores_non_trace_events()  # PRD-03-FE-011
```

### Component Tests

```python
test_trace_tab_renders_empty_state()  # PRD-03-FE-011
test_trace_tab_renders_trace_events()  # PRD-06-TRACE-001
test_trace_row_renders_event_type()  # PRD-06-TRACE-001
test_trace_row_renders_timestamp()  # PRD-06-TRACE-001
test_trace_row_renders_phase_and_status()  # PRD-06-TRACE-001
test_trace_row_renders_correlation_id()  # PRD-06-TRACE-001
test_trace_row_renders_unknown_event_safe()  # PRD-06-TRACE-001
```

### Negative Tests

```python
test_trace_event_with_null_type_rejected()  # GOV-S7-C0-009
test_trace_event_with_malformed_timestamp_rejected()  # GOV-S7-C0-009
test_trace_event_with_missing_phase_shows_unknown()  # GOV-S7-C0-009
test_static_demo_trace_not_loaded_in_live_mode()  # PRD-03-FE-011
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/trace/TraceTab.jsx (new)
- frontend/src/components/trace/TraceTimeline.jsx (new)
- frontend/src/components/trace/TraceRow.jsx (new)
- frontend/src/store/traceSlice.js (new)
- frontend/src/store/handlers/trace_event_handler.js (new)
- frontend/src/aw-ide-panel.jsx (modification at prop/callback boundaries only)
- frontend/src/main.jsx (modification for state threading only)
- tests/test_frontend_trace_timeline.py (new)
```

### Forbidden Files

```
- agent.py
- runtime/trace_events.py (read-only)
- runtime/trace_export.py (read-only)
- frontend_new_design_prototype/ (read-only)
- frontend/src/aw-workbench.jsx
```

---

## Implementation Notes

1. Create `TraceTab` component consuming `traceEntries` from frontend event store
2. Create `TraceTimeline` to render list of trace events in chronological order
3. Create `TraceRow` subcomponent to display single event
4. Add reducer/handler to process `trace_event` into frontend state
5. Show empty state before first trace event
6. Reject malformed payload with diagnostic
7. Handle unknown event types gracefully (show diagnostic row)

---

## Stop Conditions

Stop if:

- Frontend event store is not yet wired (S7-0500 incomplete)
- `trace_event` event schema missing required fields
- Tab layout does not exist
- Implementation requires touching forbidden files


---

## Evidence Recorded

- **Commit:** 7e0ab27 — Cluster 9 trace/agents components
- **Tests:** tests/test_frontend_trace_agent_cards.py (23 tests)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2467 passed / 1 skipped / 0 failed
