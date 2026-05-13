# S7-0702 — Add/Edit/Delete/Reorder/Duplicate Step UI

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0701

---

## Objective

Provide structured step editing controls in Steps tab:
- Add step: Opens form for action/locator/params/expected_outcome
- Edit step: Modifies existing step
- Delete step: Removes step from plan
- Reorder: Drag/arrow controls to move step position
- Duplicate: Create copy of step with new ID

All changes either dispatch backend commands or remain in local draft state.

---

## Source Rules

1. **PRD-03-FE-002:** Frontend does not execute edits locally without backend
2. **PRD-04-BE-001:** Backend owns step lifecycle
3. **PRD-03-FE-006:** Disabled reasons shown when backend cannot accept command

---

## Current Known Context

### What exists

- Design prototype shows step edit UI
- No edit form components
- No drag/reorder logic

### What gaps exist

- No add_step form
- No edit_step form
- No reorder/delete UI
- Backend command wiring unclear

---

## Tests First

### Unit Tests

```
test_add_step_form_validation()
test_edit_step_command_includes_step_id()
test_delete_step_command_sends_step_id()
test_reorder_updates_position_only()
test_duplicate_creates_new_step_id()
```

### Component Tests

```
test_add_step_form_opens_and_closes()
test_edit_form_pre-fills_existing_step_values()
test_delete_button_shows_confirmation()
test_reorder_arrows_update_order()
test_duplicate_button_creates_copy()
```

### Negative Tests

```
test_required_fields_prevent_submit()
test_null_step_id_rejected()
test_empty_action_blocked()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/steps/AddStepForm.jsx`
- **New:** `frontend/src/components/steps/EditStepForm.jsx`
- **New:** `frontend/src/commands/step_commands.js` (extend or create)
- **New:** `tests/test_frontend_step_editing.py`
- **Modify:** `frontend/src/components/steps/StepItem.jsx` (add controls)

### Forbidden Files

- No backend step execution logic
- No local step recording

---

## Implementation Notes

### Approach

1. Add step form:
   - Fields: action (dropdown), locator (text), params (JSON), expected_outcome (optional)
   - Submit → dispatch add_step command or save to draft

2. Edit form:
   - Pre-fill from existing step
   - Submit → dispatch edit_step command

3. Delete:
   - Button with confirmation
   - Dispatch delete_step command

4. Reorder:
   - Drag handle or up/down arrows
   - Dispatch reorder_step command with new position

5. Duplicate:
   - Button that creates copy with new step_id
   - Either local draft or backend command

### Key Invariants

- No local execution
- Backend decides if command accepted
- Disabled reasons shown

---

## Acceptance Criteria

- [ ] Add step form opens and collects inputs
- [ ] Edit step form pre-fills and updates
- [ ] Delete shows confirmation
- [ ] Reorder updates step position
- [ ] Duplicate creates new step with correct ID
- [ ] All commands dispatched to backend
- [ ] Disabled state shown when backend cannot accept
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] Forms created and tests pass
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Backend step command structure undefined
- Form complexity exceeds single component scope
