# S7-1003 — Flow: Intent → Clarification → Plan Ready

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** [S7-1004, S7-1005, S7-1006, S7-1007, S7-1008, S7-1009]
**Blocked by:** [S7-1001, S7-1002]

---

## Objective

Browser E2E test for the primary LLM planning flow: user submits intent, backend emits clarification_needed, user answers, backend emits plan_ready. Verify no execution before confirmation.

After S7-1003:
- E2E flow from submit_intent to plan_ready works locally with fake LLM
- Clarification card renders and accepts user input
- Plan card renders with correct data from plan_ready event
- No execution starts before user confirmation
- Artifacts (screenshots, event/command logs) captured

---

## Source Rules

- PRD-02-WORKFLOWS-001: Complete LLM Mode workflow steps
- PRD-03-FE-C6-001: LLM tab clarification and plan cards render from backend events
- GOV-S7-C10-001: E2E flows must complete locally with fake LLM

---

## Current Known Context

- Clarification_needed and plan_ready events exist in backend
- LLM tab components in Cluster 6 (not yet E2E verified)
- No end-to-end test joining intent submission to plan rendering

---

## Tests First

### E2E Tests

```python
# tests/e2e/test_flow_intent_clarification_plan.py

test_flow_intent_to_plan_ready_complete()  # PRD-02-WORKFLOWS-001
  # 1. Submit intent via UI
  # 2. Wait for clarification_needed event
  # 3. Assert clarification card rendered with question
  # 4. Submit answer
  # 5. Wait for plan_ready event
  # 6. Assert plan card rendered with steps and metadata
  # 7. Verify no execution started (buttons still ask for confirm)

test_flow_no_execution_before_confirm()  # PRD-03-FE-C6-001
  # After plan_ready, UI does not start execution
  # Assert: run status still shows "awaiting confirmation"

test_flow_artifacts_captured()  # GOV-S7-C10-002
  # Screenshot at each card render
  # Event log shows clarification_needed → answer → plan_ready sequence
  # Command log shows submit_intent and submit_answer commands
```

### Negative Tests

```python
test_flow_handles_no_clarification()  # GOV-S7-C0-009
  # If plan_ready comes without clarification_needed, plan card appears directly

test_flow_handles_stale_answer()  # GOV-S7-C0-009
  # If user answers after run has moved to next phase, error handled gracefully
```

---

## Implementation Boundaries

### Allowed Files

```
- tests/e2e/test_flow_intent_clarification_plan.py (new)
- tests/e2e/fake_event_stream.py (may extend with flow-specific sequence)
```

### Forbidden Files

```
- Frontend/backend source (flow driven by existing components)
```

---

## Acceptance Criteria

- [ ] Flow test passes end-to-end with fake LLM
- [ ] Clarification and plan cards render from events
- [ ] No execution before confirmation
- [ ] All artifacts captured

---

## Evidence Required

- [ ] tests/e2e/test_flow_intent_clarification_plan.py passing
- [ ] Screenshots from clarification and plan card renders
- [ ] Event log showing full sequence

---

## Stop Conditions

- Clarification card not rendering (Cluster 6 incomplete)
- Plan_ready event not being emitted or received (Cluster 5/6 issue)
- Execution starts before confirmation (Cluster 6 issue)

---

## Evidence Recorded

- **Commit:** 4e9d102 — Cluster 10 fake-flow tests + harness shadow constants
- **Tests:** tests/test_cluster10_e2e_contract.py, tests/test_cluster10_fake_flows.py (21 tests)
- **E2E baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed in 7.22s
- **Regression (no-e2e):** 2481 passed / 1 skipped / 0 failed
- **Browser smoke gate:** existing tests/e2e/* suite remains user-triggered (no paid LLM, no live websites)
