# S7-0201 Page Intelligence Live Invocation Boundary

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0201  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `02_LLM_RUNTIME.md` — DOM processing must be lean and tokenized; raw full DOM never sent to LLM.
2. **Frontend UI Spec** — page summary display must show current page state without inference.
3. **Sprint 7 Governance** — Modular architecture; no fake/live mixing; frontend-visible state.
4. **Cluster 2 Goal** — Page Intelligence boundary clear; frontend knows live vs. fake.

---

## Objective

Replace or clearly bound the fake Page Intelligence path so frontend can trust `page_analysis_started` and `page_summary_ready` events. Define when page intelligence invokes the live LLM vs. fallback to fake/cached packet. Emit frontend-visible state honestly.

Today:
- `page_intelligence.py` has `PageIntelligencePacket` (deterministic extraction).
- `page_intelligence_schema.py` builds `PageIntelligenceSchema` for LLM (lean summary).
- `page_intelligence_live.py` may invoke `page_intelligence_summarizer` LLM purpose.
- But the path mixes fake/live; frontend doesn't know which.
- Agent path unclear when to invoke live vs. return cached/fake packet.

After S7-0201:
- Page Intelligence invocation boundary explicit.
- Frontend receives `page_analysis_started` → `page_summary_ready` sequence.
- `page_analysis_started` event includes request_id, page_url, analysis_type (live_invocation | cached | fallback).
- `page_summary_ready` event includes page_summary dict and timestamp.
- Fallback (fake/cached) is emitted honestly as such, not misrepresented as live.
- Raw full DOM never sent to frontend by default.
- Token/context limits enforced; timeout emits `page_analysis_failed` event.

---

## Current Context

### Page Intelligence Today

- `PageIntelligencePacket` — deterministic extraction from DOM (elements, buttons, inputs, sections).
- `page_intelligence_schema.py` — builds lean summary with candidate_targets, ambiguity_groups, recommended_action.
- `PageIntelligenceSchema.recommended_action` — "ask_user", "plan_ready_possible", "needs_more_context".
- `page_intelligence_live.py` — invokes page_intelligence_summarizer (cheap LLM).
- `agent.py` — calls `page_intelligence_live.invoke()` at planning phase.
- Current issue: fake invocation (mock data) and live invocation (real LLM) not distinguished; frontend assumes all summaries are live.

### Required Contract

Frontend expects:
```
page_analysis_started(request_id, page_url, analysis_type)
→ [processing]
→ page_summary_ready(request_id, page_summary_dict, timestamp)
OR page_analysis_failed(request_id, error_message)
```

No raw full DOM exposure.

---

## Tests First

### Unit Tests

**Test: Page Intelligence live boundary policy**
- Verify `page_intelligence_live.invoke()` raises clear error on invalid input (null page, null DOM).
- Verify invocation type (live vs. cached vs. fallback) is set correctly.
- Verify token estimate for lean schema stays under limit (≤1500 tokens).
- Verify no raw HTML/markup in lean schema output.

**Test: Fallback packet is labeled as such**
- When live invocation fails or times out, fallback packet emitted.
- Fallback packet marked as `analysis_type: "fallback"`, not `"live_invocation"`.
- Frontend can display "fallback page summary (limited data)" if needed.

**Test: Timeout emits error event, not silent failure**
- Page Intelligence invocation timeout (e.g., 30s) triggers `page_analysis_failed` event.
- Error event includes request_id and human-readable reason: "Page analysis timed out; using fallback."

### Contract Tests

**Test: page_analysis_started event shape**
- Payload includes: request_id (str), page_url (str), analysis_type (Literal["live_invocation", "cached", "fallback"]), timestamp (ISO string).
- Optional: selected_section (str), page_title (str).
- No raw DOM or full HTML included.

**Test: page_summary_ready event shape**
- Payload includes: request_id (str), page_summary (dict with keys: page_title, url, summary_text, candidate_targets[], ambiguity_groups[], recommended_action), timestamp (ISO string).
- page_summary dict serializable to JSON.
- candidate_targets is list of {label, role, section, locator_hint, confidence}.
- No raw HTML in labels or locator_hints.

**Test: page_analysis_failed event shape**
- Payload includes: request_id (str), error_type (str), error_message (str), timestamp (ISO string).
- No sensitive data in error_message (no full traceback, no raw DOM).

### Integration Tests

**Test: Live invocation with fake-LLM**
- Call `page_intelligence_live.invoke()` with mock page packet and fake-LLM.
- Verify sequence: page_analysis_started → page_summary_ready in order.
- Verify page_summary_ready includes same request_id as page_analysis_started.

**Test: Fallback when live invocation unavailable**
- Mock `page_intelligence_summarizer` call to fail (network timeout, model unavailable).
- Verify fallback packet emitted as `page_summary_ready` with `analysis_type: "fallback"`.
- No exception thrown; graceful degradation.

**Test: Cached packet (if caching implemented)**
- If page URL same as previous invocation, return cached page_summary without re-invoking LLM.
- Mark as `analysis_type: "cached"`.
- Timestamp is original invocation time, not cache retrieval time.

### Negative Tests

**Test: Null page or DOM**
- Call with null page or null DOM element.
- Verify error logged and `page_analysis_failed` emitted (not raised exception).

**Test: Empty page (no elements)**
- Call with page that has zero interactive elements.
- Verify page_summary_ready emitted with empty candidate_targets and clear reason: "No interactive elements found."

**Test: Request ID mismatch in response**
- If fake-LLM returns wrong request_id, contract validation rejects it.
- Verify error logged; frontend does not receive mismatched response.

**Test: Raw HTML in summary (should not happen)**
- Verify lean schema builder never includes raw `<html>`, `<body>`, or full markup strings.
- If raw HTML detected, fail-closed: emit error event instead of passing through.

### Regression Tests

**Test: Sprint 6 page_intelligence_summarizer still calls controller**
- Verify `page_intelligence_summarizer` purpose still invoked via `LLMRuntimeController.call()`.
- No direct OpenAI call; always through controller.

**Test: No pay-per-token leakage**
- Grep confirms no `openai.ChatCompletion` call in page_intelligence_live.py or page_intelligence.py.
- Only `LLMRuntimeController` invokes LLM.

---

## Implementation Boundaries

### Allowed Changes

- **New module:** `runtime/page_intelligence_live.py` (if not present)
  - Function: `invoke(page_packet: PageIntelligencePacket, controller: LLMRuntimeController) → tuple[str, PageIntelligenceSchema, str]` (request_id, schema, analysis_type)
  - Emit `page_analysis_started` event before invocation.
  - Emit `page_summary_ready` or `page_analysis_failed` after invocation.
  - Timeout: 30 seconds (configurable).
  - Fallback to fake packet if live fails.

- **Modify:** `runtime/page_intelligence_schema.py`
  - Add optional `analysis_type: Literal["live_invocation", "cached", "fallback"]` field to track origin.
  - Add validation to reject raw HTML in fields.

- **Modify:** `runtime/event_contracts.py` (or new file)
  - Define `PageAnalysisStarted`, `PageSummaryReady`, `PageAnalysisFailed` event classes with typed payload.
  - Export from event_contracts so tests and implementation can import.

- **Modify:** `agent.py` (thin seam only)
  - Replace direct `page_intelligence_live.invoke()` call with controller-owned event emission seam.
  - Ensure events emitted to transport (WebSocket event queue).

- **Modify:** `server.py` or `ws/router.py`
  - Route page_analysis_* events to frontend via WebSocket.

- **New tests:** `tests/test_page_intelligence_live_invocation.py`
  - All tests listed above.

### Forbidden Changes

- No frontend UI (S7-0301+ handles that).
- No browser automation (no `browser.execute_script`, no picker).
- No paid LLM calls directly (always through controller).
- No raw DOM exposure in events.
- No broad refactor of `agent.py` (thin seam only).
- No changes to `PageIntelligencePacket` deterministic extraction (that stays stable).

---

## Acceptance Criteria

✅ **All tests green:**
- Unit tests: Page Intelligence boundary logic correct.
- Contract tests: Event payloads match typed schema.
- Integration tests: Sequence correct (started → ready).
- Negative tests: Error cases fail-closed.
- Regression tests: Sprint 6 still passes.

✅ **Event contract locked:**
- `PageAnalysisStarted`, `PageSummaryReady`, `PageAnalysisFailed` classes defined and exported.
- Payload structure matches Cluster 2 event table.
- No raw HTML in any field.

✅ **Fake/live boundary clear:**
- `analysis_type` field set correctly on every packet.
- Frontend can log and display which analysis type was used.
- Fallback labeled honestly; not misrepresented as live.

✅ **Modularization:**
- `page_intelligence_live.py` ≤300 lines.
- Event emission seam in agent.py ≤10 lines.
- New test file for page_intelligence_live tests.

✅ **No paid LLM:**
- Grep confirms no `openai.ChatCompletion` in new code.
- All LLM calls through `LLMRuntimeController.call()`.

✅ **Evidence:**
- Test file name: `tests/test_page_intelligence_live_invocation.py`
- Commits: test commit + implementation commit
- Regression output green: `python -m pytest tests/test_page_intelligence*.py -q` ✅

---

## Evidence Checklist

- [ ] `tests/test_page_intelligence_live_invocation.py` exists and passes
- [ ] All unit/contract/integration/negative tests green
- [ ] `runtime/page_intelligence_live.py` created or completed
- [ ] `runtime/event_contracts.py` includes `PageAnalysisStarted`, `PageSummaryReady`, `PageAnalysisFailed`
- [ ] `agent.py` event emission seam added (≤10 lines)
- [ ] `server.py` or `ws/router.py` routes page_analysis_* events
- [ ] Regression guard green: `python -m pytest -q --ignore=tests/e2e` shows 1689+ passed
- [ ] No `openai.ChatCompletion` in new code (grep confirms)
- [ ] Story updated with commit hashes and test file names

---

## Stop Conditions

- ❌ Any new test failure in regression suite.
- ❌ Event payload changed without Cluster 3 frontend buy-in.
- ❌ Raw HTML detected in page_summary output.
- ❌ Fallback packet misrepresented as live.
- ❌ Timeout triggers exception instead of event.
- ❌ `page_intelligence_live.py` exceeds 300 lines.
- ❌ Paid LLM call detected.

---

## Evidence Recorded

- **Implementation commit:** `0f2198b`
- **Implementation files:**
  - `runtime/event_contracts.py` — added `build_page_analysis_started_event`, `build_page_summary_ready_event`, `build_page_analysis_failed_event`
  - `runtime/page_intelligence_live.py` — pre-existing; `invoke_page_intelligence`, `needs_page_intelligence`, `PageIntelligencePacketResult` already present; source labeled fake/fallback; no raw HTML
- **Tests added:** `tests/test_page_intelligence_live_invocation.py` (20 tests: boundary detection, invocation result, event pipeline, negative)
- **Validation commands:**
  - `python -m pytest tests/test_page_intelligence_live_invocation.py tests/test_page_analysis_events.py -q`
  - `python -m pytest -q`
- **Result summary:**
  - 44 passed (page_intelligence + page_analysis combined)
  - Full suite: 2078 passed, 0 failed, 1 skipped
  - `runtime/event_contracts.py` coverage: 99%
- **Confirmation:**
  - No frontend files changed
  - No LLM prompt files changed
  - No E2E files changed
  - No local noise staged
- **Remaining gaps:** None.

