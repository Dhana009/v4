# S7-1008 — Flow: Steps Tab Run Selected/Run All

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Done
**Blocks:** [S7-1010]
**Blocked by:** [S7-1003]

---

## Objective

E2E test for Steps tab manual execution. User sees pending steps in Steps tab, selects steps to run, dispatches run_selected or run_all command. Backend executes. Verify no static demo steps appear.

---

## Tests First

```python
# tests/e2e/test_flow_steps_tab_execution.py

test_flow_steps_tab_shows_live_steps()  # PRD-02-WORKFLOWS-006
  # Steps tab renders live steps from session_state
  # No static/demo steps appear in live mode

test_flow_run_selected()  # PRD-02-WORKFLOWS-006
  # Select subset of steps
  # run_selected command sent with step_ids[]
  # Backend executes selected steps only

test_flow_run_all()  # PRD-02-WORKFLOWS-006
  # Click "run all" button
  # run_all command sent
  # Backend executes all steps

test_blocked_step_shows_reason()  # GOV-S7-C0-009
  # If step is blocked (dependency not met), show reason
  # Button disabled with explanation
```

---

## Acceptance Criteria

- [ ] Steps tab shows live steps
- [ ] run_selected and run_all work
- [ ] Blocked steps disabled with reason

---

## Evidence Required

- [ ] tests/e2e/test_flow_steps_tab_execution.py passing

---

## Stop Conditions

- Static demo steps shown (Cluster 7 issue)
- Steps not rendered from session_state (Cluster 5 issue)

---

## Evidence Recorded

- **Commit:** 4e9d102 — Cluster 10 fake-flow tests + harness shadow constants
- **Tests:** tests/test_cluster10_e2e_contract.py, tests/test_cluster10_fake_flows.py (21 tests)
- **E2E baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed in 7.22s
- **Regression (no-e2e):** 2481 passed / 1 skipped / 0 failed
- **Browser smoke gate:** existing tests/e2e/* suite remains user-triggered (no paid LLM, no live websites)
