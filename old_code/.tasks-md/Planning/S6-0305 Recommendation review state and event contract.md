# S6-0305 Recommendation review state and event contract

**Sprint:** Sprint 6  
**Cluster:** 3 (Page Intelligence + Recommendation Mode)  
**Tier:** 1 (core)  
**Type:** Feature / Contract  
**Status:** Planning  
**Owner:** Backend Events  
**Blocks:** S6-0306, S6-0307  
**Blocked by:** S6-0304  

---

## Purpose

Add typed backend events/states for recommendation review. Recommendation state transitions, accept/remove/reorder commands, accepted recommendations convert to draft executable plan. The scenario spec requires broad page recommendation requests to enter recommendation mode, not execution.

---

## Source rules

- Scenario spec: broad recommendation request → recommendation mode (not execution)
- Cluster 2 event contract is in place (S6-0205, S6-0206)
- Recommendations have stable IDs (from S6-0304)
- User must explicitly confirm before execution

---

## What it contains

```
- page_analysis_requested event
- page_summary_ready event
- validation_recommendations_ready / recommendation_ready event
- recommendation_review state
- accept/remove/reorder recommendation commands
- accepted recommendations convert to draft executable plan
```

---

## What it must NOT contain

```
- no frontend visual implementation
- no automatic execution
- no mutation without explicit user action
```

---

## Tests first

### Unit tests

```
- recommendation state transitions (requested → ready → reviewing → accepted/removed)
- recommendation IDs stable when order changes
- accepted vs unaccepted recommendations tracked
```

### Contract tests

```
- recommendation events have typed envelope
- unaccepted recommendation cannot execute
- accepted recommendations become plan draft only (not executed)
- event ordering is correct (analysis → summary → recommendations → review)
```

### Integration tests

```
- broad recommendation request enters recommendation_review, not execution
- state machine enforces transitions
```

Coverage: **95% for recommendation event/state modules**

---

## Out of scope

- Do not implement frontend UI for recommendation review
- Do not execute recommendations automatically
- Do not mutate backend state without command

---

## Allowed files

```
runtime/recommendation_events.py (new)
runtime/recommendation_state.py (new)
tests/test_recommendation_events.py (new)
tests/test_recommendation_state.py (new)
Minor edits to:
  - agent.py (new event emission)
  - backend event model if needed
```

---

## Forbidden files

- No frontend code
- No execution logic
- No auto-acceptance

---

## Implementation notes

### Events (recommendation_events.py)

```
PageAnalysisRequested:
  - request_id: string
  - page_url: string
  - selected_section: optional string

PageSummaryReady:
  - request_id: string
  - page_intelligence_summary: PageIntelligenceSummary
  - timestamp: ISO8601

ValidationRecommendationsReady / RecommendationReady:
  - request_id: string
  - recommendations: PageValidationRecommenderOutput
  - timestamp: ISO8601

AcceptRecommendationCommand:
  - request_id: string
  - recommendation_ids: list[string]

RemoveRecommendationCommand:
  - request_id: string
  - recommendation_ids: list[string]

ReorderRecommendationCommand:
  - request_id: string
  - recommendation_ids: list[string] (new order)

RecommendationReviewCompleted:
  - request_id: string
  - accepted_recommendation_ids: list[string]
  - timestamp: ISO8601
```

### State (recommendation_state.py)

```
RecommendationReviewState:
  - request_id: string
  - page_url: string
  - page_summary: PageIntelligenceSummary
  - all_recommendations: list[ValidationRecommendation]
  - accepted_ids: set[string]
  - removed_ids: set[string]
  - current_order: list[string]
  - status: enum (requested / summary_ready / recommendations_ready / reviewing / completed)
```

### State machine

```
requested
  ↓ (page_summary_ready event)
summary_ready
  ↓ (recommendations_ready event)
recommendations_ready
  ↓ (accept/remove/reorder commands)
reviewing
  ↓ (review_completed)
completed
```

### Approach

1. Create `runtime/recommendation_events.py` with typed events
2. Create `runtime/recommendation_state.py` with state management
3. Update `agent.py` or event dispatcher to emit events:
   - `PageAnalysisRequested` when broad recommendation request detected
   - `PageSummaryReady` after S6-0303 completes
   - `RecommendationReady` after S6-0304 completes
4. Create command handlers:
   - `accept_recommendations(request_id, ids)`
   - `remove_recommendations(request_id, ids)`
   - `reorder_recommendations(request_id, ids)`
5. Write unit/contract tests

### Key invariants

- Unaccepted recommendations never execute
- IDs are stable across reorder/remove
- State enforces correct transitions
- Events are immutable records

---

## Validation commands

```bash
python -m pytest tests/test_recommendation_events.py -v
python -m pytest tests/test_recommendation_state.py::test_state_transitions -v
python -m pytest tests/test_recommendation_state.py::test_accept_removes_others -v
python -m pytest tests/test_recommendation_state.py::test_ids_stable_on_reorder -v
coverage run -m pytest tests/test_recommendation_*.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/recommendation_events.py` with typed events
- [ ] `runtime/recommendation_state.py` with state machine
- [ ] `tests/test_recommendation_events.py` with event tests
- [ ] `tests/test_recommendation_state.py` with state tests
- [ ] State transitions enforced
- [ ] Unaccepted recommendations tracked
- [ ] IDs stable across reorder
- [ ] Events properly ordered (analysis → summary → recommendations → review)
- [ ] 95% coverage

---

## Stop conditions

- Backend event model unclear (read Cluster 2 contracts)
- Command handlers conflicting with existing pattern (clarify with agent.py owner)

---

## Sign-off

- [x] Story is specific (add recommendation events/state)
- [x] Scope is bounded (no execution, no frontend)
- [x] Tests are first
- [x] Blocks S6-0306 (accepted recommendations → plan)
