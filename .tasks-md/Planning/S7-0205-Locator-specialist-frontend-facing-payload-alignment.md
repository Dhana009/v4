# S7-0205 Locator Specialist Frontend-Facing Payload Alignment

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0205  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `02_LLM_RUNTIME.md` (locator validation and ambiguity).
2. **Frontend UI Spec** — Locator ambiguity card must show candidates.
3. **Cluster 2 Goal** — Locator candidates structured for UI.

---

## Objective

Ensure locator specialist outputs (candidate lists, ambiguity info) are packaged as frontend-visible payloads with stable IDs, scope/risk info, and preview. Today, locator candidates exist internally but frontend-facing structure is unclear. After S7-0205, frontend receives `locator_candidates_ready(ambiguity_id, candidates[{id, label, scope, risk, locator_preview, confidence}])` event.

---

## Tests First

### Unit Tests

**Test: Candidate ID stability**
- Same DOM element → same candidate_id.
- ID based on hash of (role, label, locator_hint).

**Test: Risk assessment**
- Candidates with scope="exact" marked as low-risk.
- Candidates with scope="similar" marked as medium-risk.
- Candidates with low confidence (<0.6) marked as high-risk.

### Contract Tests

**Test: locator_candidates_ready payload**
- Fields: ambiguity_id (str), candidates (list), timestamp (ISO).
- Each candidate: {id, label, role, section, scope, risk, locator_preview, confidence}.
- scope: Literal["exact", "similar", "fuzzy"].
- risk: Literal["low", "medium", "high"].
- locator_preview: str (short summary, no raw DOM).

### Integration Tests

**Test: Locator specialist output → candidates event**
- Call locator_specialist with ambiguous DOM.
- Verify locator_candidates_ready event emitted with multiple candidates.

**Test: Frontend selection of candidate**
- Frontend sends select_locator_candidate(ambiguity_id, candidate_id).
- Backend validates candidate and uses selected locator.

### Negative Tests

**Test: Invalid candidate_id**
- Frontend sends select_locator_candidate with wrong candidate_id.
- Backend rejects; emits error event.

**Test: Duplicate candidate IDs**
- Verify candidate IDs are unique within ambiguity_id scope.

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `runtime/event_contracts.py`
  - Add: `LocatorCandidatesReady` event class.

- **Modify:** `runtime/locator_intelligence.py` or `agent_locator_handlers.py`
  - Build candidate payload with stable IDs, scope, risk assessment.

- **Modify:** `runtime/llm_runtime_controller.py` (thin seam)
  - After locator_specialist, emit locator_candidates_ready event.

- **Modify:** `server.py` or `ws/router.py`
  - Handle select_locator_candidate command.

- **New tests:** `tests/test_locator_candidates_event.py`

### Forbidden Changes

- No frontend UI.
- No locator validation in frontend.
- No raw DOM in candidates.

---

## Acceptance Criteria

✅ **All tests green.**
✅ **Candidate IDs stable and unique.**
✅ **Risk assessment correct.**
✅ **Event payload structured for UI.**
✅ **Evidence: test file, commits, regression green.**

---

## Stop Conditions

- ❌ Regression failure.
- ❌ Unstable candidate IDs.
- ❌ Raw DOM in locator_preview.

