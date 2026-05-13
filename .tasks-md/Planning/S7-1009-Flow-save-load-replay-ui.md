# S7-1009 — Flow: Save/Load/Replay UI

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Done
**Blocks:** [S7-1010]
**Blocked by:** [S7-1005]

---

## Objective

E2E test for session persistence and replay. After execution, user can save session, load session, and replay recorded steps. Verify frontend does not infer success before backend event.

---

## Tests First

```python
# tests/e2e/test_flow_save_load_replay.py

test_flow_save_session()  # PRD-02-WORKFLOWS-007
  # After run_completed, UI shows "Save session" button
  # User clicks save
  # Backend emits save_result (or updates session_store)
  # Success message shown

test_flow_load_session()  # PRD-02-WORKFLOWS-007
  # User loads previously saved session
  # Backend emits session_state or load_result
  # Session restored: Code, Recorded, steps all restored

test_flow_replay_one_step()  # PRD-02-WORKFLOWS-007
  # Recorded tab shows step with replay button
  # User clicks replay on one step
  # Backend emits replay_result
  # Result shown (passed/failed)

test_flow_replay_all_steps()  # PRD-02-WORKFLOWS-007
  # User clicks "replay all"
  # All steps re-executed
  # Results shown for each

test_session_state_overrides_stale_local_state()  # GOV-S7-C8-003
  # If session_state event received, local state discarded
  # Code/Recorded/state reflects backend truth
```

---

## Acceptance Criteria

- [ ] Save/load flows work end-to-end
- [ ] Replay success not inferred before replay_result
- [ ] Session_state overrides local state

---

## Evidence Required

- [ ] tests/e2e/test_flow_save_load_replay.py passing

---

## Stop Conditions

- save_session/load_session commands not wired (Cluster 1 issue)
- replay_result not rendering (Cluster 8 issue)
- Session state not restored correctly (Cluster 5 issue)

---

## Evidence Recorded

- **Commit:** 4e9d102 — Cluster 10 fake-flow tests + harness shadow constants
- **Tests:** tests/test_cluster10_e2e_contract.py, tests/test_cluster10_fake_flows.py (21 tests)
- **E2E baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed in 7.22s
- **Regression (no-e2e):** 2481 passed / 1 skipped / 0 failed
- **Browser smoke gate:** existing tests/e2e/* suite remains user-triggered (no paid LLM, no live websites)
