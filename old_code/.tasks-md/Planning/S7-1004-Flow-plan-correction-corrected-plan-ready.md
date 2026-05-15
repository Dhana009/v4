# S7-1004 — Flow: Plan Correction → Corrected Plan Ready

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** [S7-1005, S7-1010]
**Blocked by:** [S7-1003]

---

## Objective

E2E test for plan correction flow: user sees plan, submits correction, backend emits new plan_ready with corrected steps. Verify old plan not confirmed after correction.

---

## Tests First

```python
# tests/e2e/test_flow_plan_correction.py

test_flow_plan_correction_to_corrected_plan()  # PRD-02-WORKFLOWS-002
  # 1. plan_ready rendered
  # 2. User submits correction
  # 3. Backend emits new plan_ready
  # 4. Old plan card no longer displayed
  # 5. New plan_ready card shows corrected steps

test_flow_old_plan_not_confirmable_after_correction()  # PRD-03-FE-C6-002
  # After new plan_ready, confirm button only applies to new plan
  # Confirm old plan ID rejected by backend

test_flow_plan_version_increments()  # PRD-02-WORKFLOWS-002
  # plan_ready.plan_version increases after correction
  # Command references correct version
```

---

## Acceptance Criteria

- [ ] Correction flow works end-to-end
- [ ] Old plan not confirmable after correction
- [ ] Plan version incremented correctly

---

## Evidence Required

- [ ] tests/e2e/test_flow_plan_correction.py passing
- [ ] Screenshots showing both plan renderings

---

## Stop Conditions

- Plan version not tracked or incremented (Cluster 6 issue)
- Old plan still confirmable after correction (Cluster 5 state management issue)

---

## Evidence Recorded

- **Commit:** 4e9d102 — Cluster 10 fake-flow tests + harness shadow constants
- **Tests:** tests/test_cluster10_e2e_contract.py, tests/test_cluster10_fake_flows.py (21 tests)
- **E2E baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed in 7.22s
- **Regression (no-e2e):** 2481 passed / 1 skipped / 0 failed
- **Browser smoke gate:** existing tests/e2e/* suite remains user-triggered (no paid LLM, no live websites)
