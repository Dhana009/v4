# S7-1006 — Flow: Locator Ambiguity → Choose Candidate

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** [S7-1010]
**Blocked by:** [S7-1003]

---

## Objective

E2E test for locator ambiguity flow. During execution, if locator matches multiple elements, backend emits locator_ambiguous. Frontend shows candidate choices. User selects. Execution continues after choice.

---

## Tests First

```python
# tests/e2e/test_flow_locator_ambiguity.py

test_flow_locator_ambiguity_to_selection()  # PRD-02-WORKFLOWS-004
  # 1. Execution in progress
  # 2. Backend emits locator_ambiguous with candidates[]
  # 3. UI shows candidate card (selectable elements with previews)
  # 4. User selects candidate
  # 5. Command dispatched with candidate_id
  # 6. Execution continues after backend validates selection

test_execution_blocked_during_ambiguity()  # GOV-S7-C0-004
  # While ambiguity card shown, execution blocked (no other actions)
  # Unresolved ambiguity stops step execution

test_invalid_candidate_selection_rejected()  # GOV-S7-C0-004
  # If user sends command with wrong candidate_id, backend rejects
  # Frontend shows error or re-prompts
```

---

## Acceptance Criteria

- [ ] Locator ambiguity flow completes
- [ ] Candidates render correctly
- [ ] Selection command sent correctly
- [ ] Execution continues post-selection

---

## Evidence Required

- [ ] tests/e2e/test_flow_locator_ambiguity.py passing
- [ ] Screenshots of candidate card

---

## Stop Conditions

- locator_ambiguous event not emitted (Cluster 2 issue)
- Candidate choice card not rendering (Cluster 6 issue)
- choose_locator_candidate command not wired (Cluster 5 issue)
