# S7-0508 — Stale, Missing ID, and Disabled Command Blocking

**Sprint:** Sprint 7  
**Cluster:** 5  
**Story:** S7-0508  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Prevent invalid commands sending. Commands with stale/missing run_id blocked. Commands disabled by state (e.g., confirm without plan) blocked. UI shows reason why command is disabled.

After S7-0508:
- confirm_plan blocked if no plan in state
- permission_decision blocked if not pending_permission
- skip_step blocked if step_id not found
- Commands include `disabled: boolean, disabledReason: string` for UI
- Buttons/cards show why disabled

---

## Tests First

### Unit Tests

**Test: Stale run_id rejection**
- Command sent with old run_id
- Current state has different run_id
- Command rejected

**Test: Missing required field rejection**
- confirm_plan without plan_id → rejected

**Test: State-disabled command**
- Skip step when not executing → rejected
- Confirm plan when no plan_ready → rejected

**Test: Disabled reason available**
- Command validation includes reason: "No active plan"
- Reason can be shown in UI

### Integration Tests

**Test: UI can check if command disabled**
- Before render, check `dispatcher.canDispatch(command_type, payload)`
- Button disabled if returns false
- Button shows reason why

---

## Acceptance Criteria

✅ **Invalid commands blocked:**
- Stale ID rejected
- Missing field rejected
- State-disabled rejected

✅ **Reasons provided:**
- UI can show why disabled

✅ **User doesn't see errors:**
- Disabled state prevents invalid commands
- No error messages if button never clicked

---

## Stop Conditions

- ❌ Command with stale run_id sent to backend
- ❌ Required field missing but command still sent
- ❌ No reason provided for disabled commands

---

## Related

- Prerequisite: S7-0507 (dispatcher)
- Depended on by: S7-0509 (UI threading)

---

## Next Story

→ S7-0509: Live prop threading into IDEPanel
