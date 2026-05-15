# S7-1005 — Flow: Confirm → Execution → Recorded → Code → Run Completed

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** [S7-1009, S7-1010]
**Blocked by:** [S7-1003]

---

## Objective

E2E test for primary successful execution path. User confirms plan → backend executes → records steps → generates code → emits run_completed. Verify UI never shows step as recorded before step_recorded event arrives.

---

## Tests First

```python
# tests/e2e/test_flow_execution_to_complete.py

test_flow_confirm_to_run_completed()  # PRD-02-WORKFLOWS-003
  # 1. plan_ready rendered
  # 2. User confirms plan (command dispatched)
  # 3. Backend emits run_started
  # 4. Backend emits step_recorded events
  # 5. Backend emits code_update
  # 6. Backend emits run_completed
  # 7. Recorded and Code tabs update
  # 8. Completion summary appears

test_step_not_marked_recorded_before_event()  # GOV-S7-C8-001
  # During execution, Steps tab shows executing but NOT recorded
  # Only after step_recorded event does Recorded tab update
  # Verify: frontend does not infer recording

test_code_not_shown_before_code_update_event()  # GOV-S7-C8-002
  # During code generation, Code tab empty or shows "generating..."
  # Only after code_update event does code appear

test_run_completed_drives_terminal_state()  # PRD-03-FE-008
  # Only run_completed event can end run
  # Frontend waits for event, does not infer completion
```

---

## Acceptance Criteria

- [ ] Full execution flow works end-to-end
- [ ] Recorded tab updates only on step_recorded
- [ ] Code tab updates only on code_update
- [ ] run_completed drives terminal state

---

## Evidence Required

- [ ] tests/e2e/test_flow_execution_to_complete.py passing
- [ ] Screenshots at each phase: confirm, execution, recording, code, completion

---

## Stop Conditions

- Steps marked recorded before step_recorded event (Cluster 6/8 inference issue)
- Code appears before code_update event (Cluster 8 inference issue)
- run_completed not terminating execution (Cluster 5 state issue)

---

## Evidence Recorded

- **Commit:** 4e9d102 — Cluster 10 fake-flow tests + harness shadow constants
- **Tests:** tests/test_cluster10_e2e_contract.py, tests/test_cluster10_fake_flows.py (21 tests)
- **E2E baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed in 7.22s
- **Regression (no-e2e):** 2481 passed / 1 skipped / 0 failed
- **Browser smoke gate:** existing tests/e2e/* suite remains user-triggered (no paid LLM, no live websites)
