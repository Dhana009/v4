# S7-0507 — Typed Command Dispatcher

**Sprint:** Sprint 7  
**Cluster:** 5  
**Story:** S7-0507  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Create typed command dispatcher. Components call dispatcher with command type and payload. Dispatcher validates before sending (required IDs present, state allows command). Commands serialized and sent via WebSocket.

After S7-0507:
- Command types defined (confirm_plan, permission_decision, skip_step, etc.)
- Dispatcher validates commands before send
- Commands include required run_id/plan_id/step_id
- WebSocket transport called for valid commands
- Invalid commands logged (not sent)

---

## Tests First

### Unit Tests

**Test: Dispatch valid command**
- `dispatcher.dispatch({type: 'confirm_plan', payload: {run_id, plan_id, plan_version}})`
- Command validated (all required fields present)
- Sent to transport (mocked)

**Test: Dispatch invalid command**
- Missing run_id → command rejected (not sent)
- Invalid payload → command rejected

**Test: Command type validation**
- Unknown command type → rejected

**Test: State-aware validation**
- confirm_plan requires state.interaction_mode='plan_review'
- If state.interaction_mode='planning' → command rejected

### Contract Tests

**Test: Command payload shapes**
- confirm_plan: {run_id, plan_id, plan_version}
- permission_decision: {run_id, operation, decision}
- skip_step: {run_id, step_id}
- All types match schema

### Integration Tests

**Test: Command dispatch flow**
- User clicks "Confirm Plan" button
- Component calls `dispatcher.dispatch(confirm_plan)`
- Dispatcher validates
- Command sent to transport
- No error thrown

---

## Acceptance Criteria

✅ **Dispatcher validates:**
- Required fields checked
- State-aware validation works

✅ **Commands sent correctly:**
- Valid commands reach transport
- Invalid commands rejected before send

✅ **Types defined:**
- All command types have type definitions
- Importable by components

---

## Stop Conditions

- ❌ Command sent without required run_id
- ❌ Invalid command not rejected
- ❌ Unknown command type not rejected

---

## Related

- Prerequisite: S7-0502 (store/state)
- Depended on by: S7-0508 (stale ID blocking)

---

## Next Story

→ S7-0508: Stale, missing ID, and disabled command blocking
