# S7-1007 — Flow: Recovery → Retry/Skip/Stop

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** [S7-1010]
**Blocked by:** [S7-1003]

---

## Objective

E2E test for failure recovery flow. Step fails, backend emits recovery_needed with suggested action (retry, skip, or stop). User chooses. Backend validates and continues or terminates.

---

## Tests First

```python
# tests/e2e/test_flow_recovery.py

test_flow_step_failure_to_recovery()  # PRD-02-WORKFLOWS-005
  # 1. Step execution fails
  # 2. Backend emits recovery_needed with suggested_action[]
  # 3. UI shows recovery card with options
  # 4. User selects action
  # 5. Command dispatched (retry_step, skip_step, or stop_run)
  # 6. Backend processes action

test_execution_blocked_during_recovery()  # GOV-S7-C0-009
  # While recovery card shown, no other execution
  # Unresolved recovery blocks completion summary

test_failed_step_not_recorded_as_pass()  # GOV-S7-C8-001
  # If step fails, Recorded tab never shows it as successful
  # If user chooses to skip, skip_step event marks it as skipped
```

---

## Acceptance Criteria

- [ ] Recovery flow completes for all actions
- [ ] Execution blocked during recovery
- [ ] Failed step not marked as successful

---

## Evidence Required

- [ ] tests/e2e/test_flow_recovery.py passing
- [ ] Screenshots of recovery card

---

## Stop Conditions

- recovery_needed not emitted (Cluster 8 issue)
- Recovery card not rendering (Cluster 6 issue)
- retry_step/skip_step commands not wired (Cluster 1 issue)
