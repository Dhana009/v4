# S7-0206 Recovery Diagnoser Frontend-Facing Payload Alignment

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0206  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `02_LLM_RUNTIME.md` (recovery flow).
2. **Frontend UI Spec** — Recovery card must show options.
3. **Cluster 2 Goal** — Recovery options structured for UI.

---

## Objective

Structure recovery_diagnoser outputs (failure analysis, recovery options) as frontend-visible `recovery_needed` event with explicit retry/skip/stop choices. Today, recovery options computed but payload structure unclear. After S7-0206, frontend renders recovery card with typed options.

---

## Tests First

### Unit Tests

**Test: Recovery option builder**
- Given failure info, create recovery options: {id, label, action, description}.
- action values: "retry", "skip", "stop".

### Contract Tests

**Test: recovery_needed payload**
- Fields: run_id (str), step_id (str), failure_reason (str), expected (str), actual (str), options (list), timestamp (ISO).
- Each option: {id, label, action, description}.
- Exactly 1+ options present.

### Integration Tests

**Test: Step failure → recovery_needed event**
- Step execution fails.
- recovery_diagnoser invoked.
- recovery_needed event emitted with options.

**Test: Frontend action selection**
- Frontend sends recovery_action(run_id, step_id, action).
- Backend processes action.

### Negative Tests

**Test: Invalid action**
- Frontend sends invalid action (not retry/skip/stop).
- Backend rejects; emits error.

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `runtime/event_contracts.py`
  - Add: `RecoveryNeeded` event class.

- **Modify:** `runtime/recovery_manager.py`
  - Build recovery_needed event payload.

- **Modify:** `runtime/llm_runtime_controller.py` (thin seam)
  - After recovery_diagnoser, emit recovery_needed event.

- **Modify:** `server.py` or `ws/router.py`
  - Handle recovery_action command.

- **New tests:** `tests/test_recovery_needed_event.py`

### Forbidden Changes

- No frontend UI.
- No execution without option.

---

## Acceptance Criteria

✅ **All tests green.**
✅ **Options explicit and typed.**
✅ **Event payload ready for UI.**
✅ **Evidence: test file, commits, regression green.**

---

## Stop Conditions

- ❌ Regression failure.
- ❌ Invalid action not rejected.

