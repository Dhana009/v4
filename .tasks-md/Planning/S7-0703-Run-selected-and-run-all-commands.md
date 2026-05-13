# S7-0703 — Run Selected and Run All Commands

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0701

---

## Objective

Wire run_selected and run_all commands from Steps tab buttons. Users can select steps and run them individually, or run all pending steps. Frontend dispatches typed commands; backend handles execution.

---

## Source Rules

1. **PRD-04-BE-001:** run_selected includes step_ids[]; run_all has no step restrictions
2. **PRD-03-FE-006:** Frontend does not mark running until backend event
3. **PRD-03-FE-001:** Blocked steps show disabled reason

---

## Current Known Context

### What exists

- Backend Step Runner accepts run_selected/run_all commands
- Design prototype shows run buttons
- No command wiring

### What gaps exist

- No run button handlers
- No selected step tracking
- No disabled state logic

---

## Tests First

### Unit Tests

```
test_run_selected_command_includes_step_ids()
test_run_all_command_sends_all_runnable_steps()
test_blocked_steps_prevent_run()
```

### Component Tests

```
test_run_selected_button_requires_selection()
test_run_all_button_requires_runnable_steps()
test_run_button_disabled_with_reason_shown()
test_step_selection_checkboxes()
```

### Integration Tests

```
test_select_steps_enables_run_selected_button()
test_run_selected_dispatches_command_with_ids()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/steps/RunControls.jsx`
- **New or modify:** `frontend/src/commands/step_commands.js`
- **New:** `tests/test_frontend_run_commands.py`
- **Modify:** `frontend/src/components/steps/StepsList.jsx` (add selection)

### Forbidden Files

- No execution logic
- No step validation

---

## Implementation Notes

1. Create RunControls component:
   - "Run Selected" button (disabled if no selection)
   - "Run All" button (disabled if all steps blocked)
   - Show reasons for disabled state

2. Track selected step IDs in store

3. Dispatch commands:
   - `run_selected { run_id, step_ids[] }`
   - `run_all { run_id }`

---

## Acceptance Criteria

- [ ] Run buttons visible in Steps tab
- [ ] Selection tracking works
- [ ] Commands dispatched with correct payloads
- [ ] Disabled state shown with reason
- [ ] Frontend does not mark running until backend event
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/steps/RunControls.jsx` created
- [ ] `tests/test_frontend_run_commands.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Backend blocked step reason structure undefined
- Run command payload conflicts with backend contract
