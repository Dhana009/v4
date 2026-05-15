# S7-0609 — Recovery Needed Card

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocked by:** S7-0601, Cluster 2

---

## Objective

Render `recovery_needed` backend events as an interactive card showing:
- Failed step/operation details
- Failure type and expected vs. actual
- Evidence/artifact references
- LLM repair proposal (labeled as proposal only)
- User actions: Retry, Choose locator, Provide instruction, Skip, Stop

Dispatches `recovery_action` command; backend controls recovery flow.

---

## Source Rules

1. **PRD-04-BE-001:** recovery_needed includes step_id, failure_type, expected, actual, tried[], options[]
2. **PRD-03-FE-001:** Recovery card shows exact failure details from backend
3. **PRD-03-FE-006:** User chooses action explicitly; backend executes

---

## Current Known Context

### What exists

- Backend emits recovery_needed event
- Design prototype shows recovery card layout
- No production RecoveryCard component

### What gaps exist

- Recovery options structure
- Evidence/artifact display
- recovery_action command payloads

---

## Tests First

### Unit Tests

```
test_recovery_action_command_dispatched_with_action()
test_retry_action_includes_step_id()
```

### Component Tests

```
test_recovery_card_displays_failure_details()
test_recovery_card_shows_expected_vs_actual()
test_recovery_card_shows_tried_approaches()
test_recovery_card_renders_action_options()
test_recovery_card_labels_llm_proposal_as_proposal()
```

### Contract Tests

```
test_recovery_needed_event_includes_failure_type()
test_recovery_options_have_id_label_action()
```

### Negative Tests

```
test_missing_failure_type_handled_safely()
test_empty_options_shows_stop_only()
```

### Integration Tests

```
test_recovery_needed_event_shows_card()
test_action_selection_dispatches_recovery_action_command()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/cards/RecoveryCard.jsx`
- **New:** `frontend/src/commands/recovery_commands.js`
- **New:** `tests/test_frontend_recovery_card.py`

### Forbidden Files

- No recovery logic (backend-owned)
- No locator improvement (S7-0707 scope)

---

## Implementation Notes

### Approach

1. Recovery Card:
   - Header: "Recovery Needed — Step N"
   - Failure details: type, expected, actual
   - Tried approaches list
   - LLM repair proposal (collapsible, labeled proposal)
   - Action buttons: Retry, Choose locator, Provide instruction, Skip, Stop

2. Command:
   - `recovery_action { run_id, step_id, action: "retry" | "skip" | "stop" | "provide_instruction", instruction?: string }`

3. State:
   - Card visible until recovery_* event
   - Cannot be dismissed

### Key Invariants

- User chooses action explicitly
- Backend decides execution
- Repair proposal labeled as proposal

---

## Acceptance Criteria

- [ ] RecoveryCard displays failure details
- [ ] Tried approaches shown
- [ ] Action options available
- [ ] LLM proposal labeled as proposal (not instruction)
- [ ] recovery_action command sent with user choice
- [ ] Card cannot be dismissed without action
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/cards/RecoveryCard.jsx` exists
- [ ] `tests/test_frontend_recovery_card.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Recovery options structure undefined
- Card requires recovery execution logic

---

## Evidence Recorded

- **Commit:** a84bf22 — Cluster 6 LLM card extraction
- **File:** `frontend/src/components/llm/` — RecoveryCard.jsx — retry_recovery/skip_step/stop_run typed; no success inference
- **Test:** tests/test_frontend_llm_cards.py (36 tests verify typed commands, empty states, no demo, no local lifecycle mutation)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2383 passed / 1 skipped / 0 failed
