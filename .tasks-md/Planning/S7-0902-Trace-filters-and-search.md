# S7-0902 — Trace Filters and Search

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0901]

---

## Objective

Add filtering and search UI to Trace timeline. Filter by source (backend/LLM/frontend/replay), severity (error/warning/info), and event type. Search by step_id or event type. Filtering is local UI only; does not affect backend state. Clear filters restores full timeline.

After S7-0902:
- Filter buttons/dropdown visible
- Search input filters trace by step_id/event type
- Filter state persists during session
- Clearing filters restores full timeline
- No backend API calls for filtering

---

## Source Rules

- PRD-06-TRACE-002: Trace filtering and search UI
- PRD-03-FE-007: Frontend filtering is local; does not mutate backend state

---

## Current Known Context

### What exists
- S7-0901 renders trace timeline
- `traceEntries[]` in frontend store

### What gaps exist
- No filter UI components
- No search input
- No filter logic in reducer

---

## Tests First

### Unit Tests

```python
test_filter_trace_by_source()  # PRD-06-TRACE-002
test_filter_trace_by_severity()  # PRD-06-TRACE-002
test_search_trace_by_step_id()  # PRD-06-TRACE-002
test_search_trace_by_event_type()  # PRD-06-TRACE-002
test_clear_filters_restores_all_events()  # PRD-06-TRACE-002
```

### Component Tests

```python
test_filter_ui_renders()  # PRD-06-TRACE-002
test_search_input_filters_in_realtime()  # PRD-06-TRACE-002
test_clear_filters_button_resets()  # PRD-06-TRACE-002
```

### Negative Tests

```python
test_empty_search_shows_all_events()  # PRD-06-TRACE-002
test_no_results_shows_empty_state()  # PRD-06-TRACE-002
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/trace/TraceFilters.jsx (new)
- frontend/src/store/traceSlice.js (extend)
- tests/test_frontend_trace_timeline.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/trace_events.py
- frontend_new_design_prototype/
```

---

## Stop Conditions

Stop if:

- Coverage below 95%

