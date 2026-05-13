# S7-0502 — Frontend Reducer and Event Store

**Sprint:** Sprint 7  
**Cluster:** 5  
**Story:** S7-0502  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Source Rules

1. **Cluster 5 Goal** — event-driven state management
2. **Architecture rule** — backend owns runtime truth

---

## Objective

Create frontend event store using reducer pattern. Events from backend trigger state transitions. State is pure (no side effects in reducer). Components subscribe to state and re-render when state changes.

After S7-0502:
- Event store module created (`frontend/src/store/`)
- Reducer function handles all event types
- State shape typed and defined
- No inference of lifecycle truth (only from backend events)
- Store testable without React

---

## Current Context

- State logic mixed in main.jsx and component props
- No typed reducer
- No event store

---

## Tests First

### Unit Tests

**Test: Reducer pure function**
- Call reducer(state, event)
- Returns new state object (not mutated)
- No side effects

**Test: Initial state**
- `createInitialState()` returns complete state shape
- All required fields present
- Defaults correct (idle, no plan, etc.)

**Test: Plan ready event**
- `reducer(state, {type: 'plan_ready', payload: {...}})`
- Returns state with: plan_id, plan, interaction_mode='plan_review'
- Other fields unchanged

**Test: Step lifecycle events**
- `step_validating` → interaction_mode stays same, step state updates
- `step_executing` → similar
- `step_failed` → step marked failed, interaction_mode may become recovery
- `step_skipped` → step marked skipped

**Test: Run completed event**
- `run_completed` → interaction_mode='completed', summary populated

**Test: No inference**
- Run started but no plan_ready yet → interaction_mode='planning'
- Code_update received but no run_completed → interaction_mode not changed to 'completed'
- Only events drive state, never inferred

### Contract Tests

**Test: State shape contract**
- State includes: run_id, plan_id, plan, pending_steps[], recorded_steps[], interaction_mode, errors[], etc.
- All fields typed correctly
- No extraneous fields

**Test: Event/state immutability**
- Reducer never mutates input state
- New state returned
- Old state unchanged

### Integration Tests

**Test: Event sequence → state transitions**
- run_started → planning state
- plan_ready → plan_review state
- confirm_plan command (user) → plan becomes confirmed
- (backend emits step_validating) → executing state
- step_recorded → recorded_steps updated
- run_completed → completed state

**Test: State snapshot and restore**
- Save state to object
- Restore from object
- State is same

### Negative Tests

**Test: Unknown event**
- `reducer(state, {type: 'unknown'})`
- Returns state unchanged (safe)
- No error thrown

**Test: Malformed payload**
- Missing required field in event payload
- Reducer handles gracefully
- State not corrupted

**Test: Conflicting events**
- run_completed received, then step_validating (out of order)
- Reducer handles (step_validating may be ignored or processed)
- State remains valid

---

## Implementation Boundaries

### Allowed Changes

- **New module:** `frontend/src/store/` (or `frontend/src/store.js`)
  - Export: `reducer(state, event)` pure function
  - Export: `createInitialState()` function
  - Export: `FrontendState` type
  - Max 300 lines for reducer

- **Modify:** main.jsx (wiring only, ≤10 lines)

- **New tests:** `tests/test_frontend_reducer.py` or TS test file

### Forbidden Changes

- No component logic in reducer
- No side effects in reducer
- No direct DOM manipulation

---

## Acceptance Criteria

✅ **Reducer pure and testable:**
- No side effects
- Input state never mutated
- Output correct for all event types

✅ **State shape defined:**
- All fields typed
- Complete initialization
- No inference of lifecycle truth

✅ **Store created:**
- Exported and importable
- No React dependency yet (store is pure JS/TS)

✅ **Tests passing:**
- Unit, contract, integration, negative tests green
- All event types tested
- Regression baseline maintained

---

## Stop Conditions

- ❌ Reducer mutates input state
- ❌ Reducer has side effects (network, DOM, etc.)
- ❌ Frontend infers lifecycle truth from events (e.g., assumes run complete from last step)
- ❌ Unknown event crashes reducer
- ❌ State shape incomplete

---

## Related

- Prerequisite: S7-0501 (event types)
- Depended on by: S7-0503 (store consumers)

---

## Next Story

→ S7-0503: Session_state consumer and reconnect restore
