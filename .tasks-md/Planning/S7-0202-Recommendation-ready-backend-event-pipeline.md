# S7-0202 recommendation_ready Backend Event Pipeline

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0202  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `01_PRODUCT_WORKFLOWS.md` (plan review workflow) and `04_BACKEND_EVENT_CONTRACT.md` (event emissions).
2. **Frontend UI Spec** — Recommendation review cards must render typed backend data.
3. **Sprint 6 Handoff** — Recommendation infrastructure exists; needs frontend pipeline.
4. **Cluster 2 Goal** — Recommendations become frontend-visible typed events.

---

## Objective

Make recommendation results from `page_validation_recommender` LLM purpose emit as typed `recommendation_ready` backend events that the frontend can render in review cards. Today, recommendations exist as controller outputs but are not emitted as events. After S7-0202, frontend receives `recommendation_ready(request_id, recommendations[], timestamp)` event that it can render and respond to with `accept_recommendation` or `reject_recommendation` commands.

---

## Current Context

### Recommendation Infrastructure Today

- `page_validation_recommender` LLM purpose — reviews page and suggests actions (fill, click, assert).
- `recommendation_state.py` — manages recommendation state.
- `recommendation_events.py` — defines `RecommendationReady` dataclass (request_id, recommendations, timestamp).
- `recommendation_contracts.py` — validates recommendation schema.
- `agent.py` — calls `page_validation_recommender` but does not emit events.
- Current issue: recommendations generated but not exposed to frontend as events.

### Required Contract

Frontend expects:
```
recommendation_ready(
  request_id: str,
  recommendations: [
    {
      id: str,
      type: Literal["fill", "click", "assert"],
      target: {label, role, section, locator},
      reason: str,
      confidence: float
    }
  ],
  timestamp: ISO string
)
```

---

## Tests First

### Unit Tests

**Test: Recommendation builder creates valid payload**
- Given a page_validation_recommender output, create RecommendationReady payload.
- Verify all required fields present.
- Verify recommendation_ids are stable (same output → same IDs).

**Test: Recommendations filtered by confidence threshold**
- If confidence < 0.5, recommendation is not included by default.
- Configurable threshold respected.

**Test: Recommendation grouping by section**
- Recommendations grouped by page section for UI display.
- Verify grouping logic is deterministic.

### Contract Tests

**Test: RecommendationReady event shape**
- Payload includes: request_id (str), recommendations (list), timestamp (ISO string).
- Each recommendation has: id (stable str), type (Literal["fill", "click", "assert"]), target (dict), reason (str), confidence (float).
- No raw DOM or full markup in target.
- target dict keys: label (str), role (str), section (str), locator_hint (str).

**Test: Recommendation ID stability**
- Same recommendation output → same ID.
- ID based on hash of (type, target, reason) to ensure determinism.
- ID not randomly generated per invocation.

### Integration Tests

**Test: page_validation_recommender output → recommendation_ready event**
- Call `page_validation_recommender` with fake-LLM and mock page.
- Verify output converted to RecommendationReady event.
- Verify event emitted to transport.

**Test: Frontend command acceptance**
- Frontend sends `accept_recommendation(request_id, recommendation_ids[])`.
- Backend processes acceptance (recommendations become plan inputs).
- Verify no execution starts without acceptance confirmation.

**Test: Frontend rejection command**
- Frontend sends `reject_recommendation(request_id, recommendation_ids[])`.
- Backend removes rejected recommendations from consideration.
- Verify subsequent plan does not include rejected recommendations.

### Negative Tests

**Test: Invalid recommendation payload rejected**
- If page_validation_recommender returns malformed output (missing type, invalid confidence, null target), recommendation skipped.
- Event still emitted but with fewer recommendations (not crash).

**Test: Empty recommendation list handled**
- Page analysis shows no recommendations available.
- recommendation_ready emitted with empty recommendations[].
- Frontend can display "No suggestions available" state.

**Test: Stale request_id ignored**
- Frontend sends accept/reject with old request_id (different page analysis).
- Backend validates request_id matches current context.
- Stale command rejected with error event.

**Test: No execution without acceptance**
- Recommendation is not used to auto-build plan.
- Frontend must send explicit accept command.
- Recommendations are advisory only.

### Regression Tests

**Test: page_validation_recommender still invoked via controller**
- Verify controller call site for page_validation_recommender purpose unchanged.
- No direct OpenAI call; always through controller.

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `runtime/recommendation_events.py`
  - Ensure `RecommendationReady` dataclass is complete and matches frontend contract.
  - Add optional fields if needed (grouping info, confidence threshold used).

- **Modify:** `runtime/recommendation_state.py`
  - Add method: `build_event_payload(page_validation_recommender_output: dict) → RecommendationReady`.
  - Ensure recommendation IDs are stable (deterministic hash).

- **Modify:** `runtime/llm_runtime_controller.py` (thin seam only)
  - After `page_validation_recommender` invocation completes, emit `recommendation_ready` event.
  - Hook event to transport.

- **Modify:** `agent.py` (thin seam only)
  - Ensure `page_validation_recommender` invocation triggers event emission.
  - No new logic; just threading.

- **Modify:** `server.py` or `ws/router.py`
  - Define command handlers: `handle_accept_recommendation`, `handle_reject_recommendation`.
  - Update recommendation_state on command receipt.

- **New tests:** `tests/test_recommendation_event_pipeline.py`
  - All tests listed above.

- **New if needed:** `tests/test_recommendation_acceptance_integration.py`
  - Integration tests for accept/reject flow.

### Forbidden Changes

- No frontend UI (S7-0301+ handles that).
- No browser automation.
- No paid LLM calls.
- No silent acceptance (frontend must confirm).
- No executing recommendation without user acceptance.
- No broad agent.py refactor.

---

## Acceptance Criteria

✅ **All tests green:**
- Unit tests: Recommendation builder logic.
- Contract tests: RecommendationReady event payload.
- Integration tests: LLM output → event → command flow.
- Negative tests: Invalid payloads, stale IDs, empty lists.
- Regression tests: Controller call site unchanged.

✅ **Event contract locked:**
- `RecommendationReady` fully defined and exported.
- All frontend-facing fields stable and typed.
- No raw DOM in recommendation data.

✅ **Command handlers defined:**
- `handle_accept_recommendation` processes acceptance.
- `handle_reject_recommendation` processes rejection.
- Both validate request_id and recommendation_ids.

✅ **No auto-execution:**
- Recommendations never used to auto-build plan.
- Frontend must send explicit command.
- No silent state changes on event receipt.

✅ **Evidence:**
- Test file: `tests/test_recommendation_event_pipeline.py`
- Commits: test + implementation
- Regression green: `python -m pytest tests/test_recommendation*.py -q` ✅

---

## Evidence Checklist

- [ ] `tests/test_recommendation_event_pipeline.py` exists and passes
- [ ] All unit/contract/integration/negative tests green
- [ ] `runtime/recommendation_events.py` RecommendationReady complete
- [ ] `runtime/recommendation_state.py` build_event_payload() added
- [ ] `runtime/llm_runtime_controller.py` event emission seam added
- [ ] `server.py` or `ws/router.py` handles accept/reject commands
- [ ] Regression guard green
- [ ] No `openai.ChatCompletion` in new code
- [ ] Story updated with evidence

---

## Stop Conditions

- ❌ Any new regression test failure.
- ❌ Recommendation accepted without explicit command.
- ❌ Stale request_id not validated.
- ❌ Raw DOM in recommendation payload.
- ❌ Paid LLM call detected.

