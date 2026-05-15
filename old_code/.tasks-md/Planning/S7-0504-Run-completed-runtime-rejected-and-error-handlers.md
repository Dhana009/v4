# S7-0504 — Run_completed, runtime_rejected, and Error Handlers

**Sprint:** Sprint 7  
**Cluster:** 5  
**Story:** S7-0504  
**Status:** Done  
**Date:** 2026-05-14  

---

## Objective

Handle terminal backend events. `run_completed` signals end of run. `runtime_rejected` signals error. State updates correctly, interaction_mode becomes 'completed' or shows error.

After S7-0504:
- run_completed event processed (interaction_mode='completed', summary shown)
- runtime_rejected event processed (error logged, UI shows error state)
- Error context extracted and shown (not silent failures)

---

## Tests First

### Unit Tests

**Test: Run completed**
- `reducer(state, {type: 'run_completed', payload: {summary, duration, success}})`
- interaction_mode='completed'
- Summary fields populated

**Test: Runtime rejected**
- `reducer(state, {type: 'runtime_rejected', payload: {error_type, error_message}})`
- Error added to errors[] state
- Error_message visible (not generic)

**Test: Run not inferred as complete**
- Last step_recorded received
- interaction_mode NOT changed to 'completed'
- Wait for explicit run_completed event

### Negative Tests

**Test: Null error message**
- runtime_rejected with null error_message
- Handled safely (default message shown)

**Test: Unknown error_type**
- error_type not recognized
- Logged safely

---

## Acceptance Criteria

✅ **run_completed processed:**
- Mode changed to completed
- Summary shown

✅ **runtime_rejected processed:**
- Error logged
- UI shows error state

✅ **No inference:**
- Completion NOT inferred from last step
- Only explicit run_completed event triggers completed state

---

## Stop Conditions

- ❌ Frontend infers completion from events other than run_completed
- ❌ Error messages not shown to user
- ❌ Null error_message causes crash

---

## Related

- Prerequisite: S7-0502 (reducer)
- Depended on by: S7-0509 (UI threading)

---

## Next Story

→ S7-0505: Step lifecycle event handlers

---

## Evidence Recorded

- **Commit (RED):** 65eb6d6 — test_frontend_event_store_handlers.py (10 new RED tests)
- **Commit (GREEN):** 345365e — reducer extension + main.jsx threading
- **Change:** run_completed blocked when pending_recovery open; runtime_rejected appends to errors+last_error; generic error and schema_error event handlers added
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2347 passed / 1 skipped / 0 failed
