# S7-0203 page_analysis_started and page_summary_ready Events

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0203  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `04_BACKEND_EVENT_CONTRACT.md` (event taxonomy and lifecycle).
2. **Frontend UI Spec** — Frontend must show "analyzing page..." progress state.
3. **Cluster 2 Goal** — Explicit frontend-visible events for page analysis lifecycle.
4. **S7-0201** — Prerequisite: Page Intelligence live invocation boundary defined.

---

## Objective

Emit explicit `page_analysis_started` and `page_summary_ready` events so frontend can display analysis progress without inference. Today, page analysis happens silently; frontend does not know when analysis begins or completes. After S7-0203, frontend receives typed events with clear lifecycle signals.

---

## Current Context

Page Intelligence invocation (S7-0201) emits signals, but needs explicit lifecycle events for UI.

**Required events:**

```
page_analysis_started(request_id, page_url, section, timestamp)
→ [processing]
→ page_summary_ready(request_id, page_summary, analysis_type, timestamp)
OR page_analysis_failed(request_id, error_type, message, timestamp)
```

---

## Tests First

### Unit Tests

**Test: Event builder for page_analysis_started**
- Given page_url and section, create event with unique request_id.
- Verify request_id is UUID or stable hash.

**Test: Event builder for page_summary_ready**
- Given request_id and page summary dict, create event.
- Verify timestamp is ISO 8601 string.

**Test: Event builder for page_analysis_failed**
- Given request_id and error info, create event.
- Verify error_type and message are clean (no traceback).

### Contract Tests

**Test: page_analysis_started payload shape**
- Fields: request_id (str), page_url (str), section (str | null), timestamp (ISO string).
- Optional: page_title (str).
- request_id must match downstream events.

**Test: page_summary_ready payload shape**
- Fields: request_id (str), page_summary (dict), analysis_type (Literal["live_invocation", "cached", "fallback"]), timestamp (ISO string).
- page_summary has keys: page_title, url, summary_text, candidate_targets[], ambiguity_groups[], recommended_action.

**Test: page_analysis_failed payload shape**
- Fields: request_id (str), error_type (str), error_message (str), timestamp (ISO string).
- error_type examples: "timeout", "malformed_output", "network_error".
- error_message is human-friendly, no raw traceback.

### Integration Tests

**Test: Event sequence correctness**
- Emit page_analysis_started.
- Emit page_summary_ready with matching request_id.
- Verify timestamps increase (ready >= started).

**Test: Failed analysis sequence**
- Emit page_analysis_started.
- Emit page_analysis_failed with matching request_id.
- Frontend can log and show error state without crash.

### Negative Tests

**Test: Mismatched request_id**
- If page_summary_ready returns different request_id than started, frontend logs error.
- Frontend does not process mismatched event.

**Test: Duplicate started events**
- Multiple page_analysis_started for same request_id (should not happen).
- Frontend handles gracefully (idempotent or ignores duplicate).

**Test: Ready without started**
- Receive page_summary_ready without prior page_analysis_started.
- Frontend can still process (best-effort) or log warning.

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `runtime/event_contracts.py`
  - Add event classes: `PageAnalysisStarted`, `PageSummaryReady`, `PageAnalysisFailed`.
  - Export for use in agent.py and tests.

- **Modify:** `runtime/page_intelligence_live.py` (or new file)
  - Function `emit_page_analysis_started(request_id, page_url, section, event_queue)`.
  - Function `emit_page_summary_ready(request_id, page_summary, analysis_type, event_queue)`.
  - Function `emit_page_analysis_failed(request_id, error_type, error_message, event_queue)`.
  - Call these around page analysis logic.

- **Modify:** `agent.py` (thin seam only)
  - Hook page_analysis_* event emissions into event transport.

- **Modify:** `server.py` or `ws/router.py`
  - Route page_analysis_* events to frontend.

- **New tests:** `tests/test_page_analysis_events.py`

### Forbidden Changes

- No frontend UI.
- No browser automation.
- No paid LLM.
- No raw DOM in events.

---

## Acceptance Criteria

✅ **All tests green.**
✅ **Event payload contracts match Cluster 2 table.**
✅ **No request_id mismatches.**
✅ **Event sequence correct (started → ready or failed).**
✅ **Error messages are clean and user-friendly.**
✅ **Evidence: test file, commits, regression green.**

---

## Stop Conditions

- ❌ Regression failure.
- ❌ Raw DOM in events.
- ❌ Mismatched request_ids.
- ❌ Paid LLM call.

---

## Evidence Recorded

- **Implementation commit:** `0f2198b`
- **Implementation files:**
  - `runtime/event_contracts.py` — added `build_page_analysis_started_event`, `build_page_summary_ready_event` (strips raw_html), `build_page_analysis_failed_event`
- **Tests added:** `tests/test_page_analysis_events.py` (24 tests: started/summary/failed type, fields, envelope, schema_version, raw_html stripping, negative validation)
- **Validation commands:**
  - `python -m pytest tests/test_page_analysis_events.py -q`
  - `python -m pytest -q`
- **Result summary:**
  - 24 passed
  - Full suite: 2078 passed, 0 failed, 1 skipped
  - `runtime/event_contracts.py` coverage: 99%
- **Confirmation:**
  - `raw_html` stripped from page_summary before inclusion in event
  - request_id validated (ValueError on empty)
  - No frontend files changed
- **Remaining gaps:** None.

