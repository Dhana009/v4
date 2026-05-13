# S7-0704 — Picker Element and Section Integration

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0702

---

## Objective

Integrate element picker with Steps tab step editing. Users click "Pick Element" button, picker activates and allows selecting an element or section. Selected element info dispatched as pick_element command. Frontend shows selected element state in edit form.

Picker safe mode: excluded AutoWorkbench panel from picker targets.

---

## Source Rules

1. **PRD-03-FE-002:** Element picker is candidate/context only
2. **PRD-03-FE-006:** Backend validates locator before execution
3. **Frontend UI Spec:** Picker excludes AutoWorkbench UI elements

---

## Current Known Context

### What exists

- Basic picker UI exists
- No integration with Steps tab edit forms
- Picker mode activation unclear

### What gaps exist

- No "Pick Element" button in edit forms
- No picker event handlers
- No selected element state in form

---

## Tests First

### Unit Tests

```
test_arm_picker_command_includes_mode()
test_pick_element_command_includes_locator_hint()
test_picker_excluded_targets_correct()
```

### Component Tests

```
test_pick_element_button_visible_in_edit_form()
test_picker_activation_on_button_click()
test_picker_cancellation_safe()
test_selected_element_stored_in_form()
```

### Integration Tests

```
test_pick_element_flow_end_to_end()
test_cancellation_restores_form_state()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/picker/PickerController.jsx`
- **New:** `frontend/src/commands/picker_commands.js`
- **Modify:** Edit form components (add Pick Element button)
- **New:** `tests/test_frontend_picker_integration.py`

### Forbidden Files

- No real browser element picking
- No picker backend implementation

---

## Implementation Notes

1. PickerController:
   - arm_picker command on activation
   - Listen for pick_element event
   - Update form state with selected element

2. Picker safety:
   - Exclude AutoWorkbench panel DOM
   - Exclude picker UI itself

3. Form integration:
   - "Pick Element" button in add/edit forms
   - Show selected element hint in form
   - Allow clearing selection

---

## Acceptance Criteria

- [ ] Pick Element button visible in forms
- [ ] Picker activates safely
- [ ] Selected element updates form
- [ ] Picker excludes AutoWorkbench UI
- [ ] Cancel restores state
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] Components created, tests pass
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Real browser element picking required
- Picker backend integration missing
