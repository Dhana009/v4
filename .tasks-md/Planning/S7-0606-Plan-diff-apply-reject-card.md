# S7-0606 — Plan Diff Apply/Reject Card

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocked by:** S7-0601, S7-0605, Cluster 2

---

## Objective

Render `plan_diff_proposed/validated` backend events as a card showing:
- Diff operations (add/remove/reorder/replace step, change expected outcome)
- Old vs new version
- Apply/Reject buttons

Applying diff should wait for backend validation before continuing.

---

## Source Rules

1. **PRD-04-BE-001:** plan_diff_proposed includes plan_id, old_version, new_version, operations[]
2. **PRD-03-FE-001:** Diff card shows operations exactly as backend provides
3. **PRD-03-FE-006:** Backend validation required before execution

---

## Current Known Context

### What exists

- Backend can emit plan_diff events
- No PlanDiffCard component

### What gaps exist

- Diff operations structure undefined
- apply_diff/reject_diff commands not tested
- Diff visualization unclear

---

## Tests First

### Unit Tests

```
test_apply_diff_command_includes_plan_id_versions_diff_id()
test_reject_diff_command_preserves_active_plan()
```

### Component Tests

```
test_diff_card_renders_operation_rows()
test_diff_card_shows_old_and_new_version()
test_apply_and_reject_buttons_visible()
test_diff_card_disabled_state_before_validation()
```

### Contract Tests

```
test_plan_diff_payload_includes_operations()
test_diff_operation_has_type_and_target()
```

### Negative Tests

```
test_malformed_operations_handled_safely()
test_missing_diff_id_rejected()
```

### Integration Tests

```
test_plan_diff_event_shows_card()
test_apply_diff_command_dispatched()
test_new_plan_ready_shown_after_validation()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/cards/PlanDiffCard.jsx`
- **New:** `frontend/src/commands/diff_commands.js`
- **New:** `tests/test_frontend_plan_diff_card.py`

### Forbidden Files

- No local diff application
- No plan mutation

---

## Implementation Notes

### Approach

1. Render diff operations:
   - `add_step { step_id, position, description }`
   - `remove_step { step_id }`
   - `reorder_step { step_id, new_position }`
   - `change_expected_outcome { step_id, old_outcome, new_outcome }`

2. Show versions:
   - "Version X → Version Y"
   - Operations list with add/remove/reorder indicators

3. Commands:
   - `apply_diff { plan_id, old_version, new_version, diff_id }`
   - `reject_diff { plan_id, diff_id }`

### Key Invariants

- No local diff application
- Backend validates before accepting
- Reject preserves active plan

---

## Acceptance Criteria

- [ ] PlanDiffCard renders diff operations
- [ ] Operations shown as add/remove/reorder/change
- [ ] Versions clearly displayed
- [ ] Apply/Reject buttons dispatch correct commands
- [ ] No local plan modification
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/cards/PlanDiffCard.jsx` exists
- [ ] `tests/test_frontend_plan_diff_card.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Diff operation structure from backend undefined
- Card requires local plan application

---

## Evidence Recorded

- **Commit:** a84bf22 — Cluster 6 LLM card extraction
- **File:** `frontend/src/components/llm/` — PlanDiffCard.jsx — apply_plan_diff/reject_plan_diff typed; no local plan mutation
- **Test:** tests/test_frontend_llm_cards.py (36 tests verify typed commands, empty states, no demo, no local lifecycle mutation)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2383 passed / 1 skipped / 0 failed
