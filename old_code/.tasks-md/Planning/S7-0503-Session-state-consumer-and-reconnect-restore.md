# S7-0503 — Session_state Consumer and Reconnect Restore

**Sprint:** Sprint 7  
**Cluster:** 5  
**Story:** S7-0503  
**Status:** Done  
**Date:** 2026-05-14  

---

## Source Rules

1. **PRD v2.3** — session_state event contract
2. **Cluster 5 Goal** — reconnect restores UI from backend

---

## Objective

Handle `session_state` backend event specially. When frontend reconnects after network loss, backend sends `session_state` event with complete UI state (run, plan, steps, code, trace). Frontend must consume this and restore UI without duplicating records.

After S7-0503:
- `session_state` event received and processed
- All fields from session_state merge into frontend state
- Recorded steps not duplicated on reconnect
- Code preview updated if code_updated happened while offline
- Trace entries preserved

---

## Current Context

- No session_state consumer
- Frontend has no reconnect logic
- State lost on network loss

---

## Tests First

### Unit Tests

**Test: Session state applied**
- `reducer(state, {type: 'session_state', payload: {run_id, plan, ...}})`
- State updated with all fields from payload
- Previous state discarded (replaced)

**Test: No duplication**
- session_state includes recorded_steps: [step1, step2]
- Frontend state already has recorded_steps: [step1]
- After consuming session_state, recorded_steps: [step1, step2] (not [step1, step1, step2])

**Test: Merge strategy**
- session_state has newer code_preview than local state
- Code preview updated (session_state wins)

**Test: Stale session state ignored**
- Session_state timestamp older than current state
- State unchanged (or logged as warning)

### Contract Tests

**Test: Session state payload**
- Includes: run_id, session_id, plan, pending_steps[], recorded_steps[], code_preview, trace_entries[], phase
- All required fields present

### Integration Tests

**Test: Reconnect flow**
- WebSocket connects, receives session_state
- State restored from session_state
- UI re-renders with correct data

**Test: No loss of unsent commands**
- User sends message before disconnect
- Disconnect occurs
- Reconnect receives session_state
- Unsent message still queued for resend

### Negative Tests

**Test: Null session_state**
- `session_state` event with null payload
- Handled safely (state unchanged or logged)

**Test: Incomplete session_state**
- Missing plan field
- Handled gracefully (partial merge or error logged)

---

## Implementation Boundaries

### Allowed Changes

- **Extend:** `frontend/src/store/` reducer
  - Add case for 'session_state' event
  - Special handling: replace state with session_state payload
  - ≤20 lines

- **Modify:** main.jsx or transport layer (≤5 lines)
  - Ensure session_state events routed to reducer

- **New tests:** test_session_state_consumer

### Forbidden Changes

- No command queue logic (defer to later)

---

## Acceptance Criteria

✅ **Session state consumed:**
- Backend session_state event processed correctly
- State updated from payload

✅ **No duplication:**
- Recorded steps merged correctly (no duplicates)

✅ **Reconnect restores UI:**
- After network loss and reconnect, UI shows correct state

✅ **Tests passing:**
- Unit, integration tests green
- Regression baseline maintained

---

## Stop Conditions

- ❌ Session_state causes recorded steps duplication
- ❌ Session_state with missing fields causes crash
- ❌ Old session_state overwrites newer state

---

## Related

- Prerequisite: S7-0502 (reducer)
- Depended on by: S7-0504 (error handling)

---

## Next Story

→ S7-0504: Run_completed, runtime_rejected, and error handlers

---

## Evidence Recorded

- **Commit (RED):** 65eb6d6 — test_frontend_event_store_handlers.py (10 new RED tests)
- **Commit (GREEN):** 345365e — reducer extension + main.jsx threading
- **Change:** session_state restores plan, pending_steps, recorded_steps, code_preview with ?? fallbacks; recorded_steps replaced (not appended) to avoid dupes on reconnect
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2347 passed / 1 skipped / 0 failed
