# S7-0709 — Manual Action Builder

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocked by:** S7-0708

---

## Objective

Let users build manual action steps from selected element in Manual Mode. Action types: click, fill, press, hover, select option, check/uncheck, upload file, submit, navigate.

Users select action type, fill required params (target element, input value, etc.), add to step list. Backend validates before execution.

---

## Source Rules

1. **PRD-03-FE-006:** Frontend builds step draft; backend validates
2. **PRD-04-BE-001:** add_step command includes action, locator, params
3. **Cluster 7 strategy:** Manual Mode deterministic first; no LLM help unless explicit

---

## Current Known Context

### What exists

- Design prototype shows action builder
- Element picker works (S7-0704)
- No production ActionBuilder component

### What gaps exist

- No action type selector
- No param input forms per action type
- No add_step command dispatch

---

## Tests First

### Component Tests

```
test_action_dropdown_shows_all_types()
test_fill_action_requires_input_value()
test_select_option_action_requires_value()
test_upload_action_requires_file()
test_submit_action_needs_no_params()
test_add_action_dispatches_command()
test_required_fields_prevent_submit()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/manual/ActionBuilder.jsx`
- **New:** `frontend/src/components/manual/ActionTypeForm.jsx` (polymorphic)
- **Modify:** `frontend/src/commands/step_commands.js`
- **New:** `tests/test_frontend_manual_action_builder.py`

### Forbidden Files

- No backend action execution
- No local action validation

---

## Implementation Notes

1. ActionBuilder:
   - Action type dropdown
   - Conditional param form per action type
   - Add button dispatches add_step command

2. Action types with required params:
   - click: locator only
   - fill: locator, value
   - press: key
   - hover: locator
   - select option: locator, option_value
   - check/uncheck: locator
   - upload: locator, file
   - submit: locator
   - navigate: url

---

## Acceptance Criteria

- [ ] Action type selector works
- [ ] Param forms show per action type
- [ ] Required params enforced
- [ ] add_step command dispatched
- [ ] Backend validation required
- [ ] All tests pass, coverage ≥ 95%

---

## Stop Conditions

- Backend action validation structure undefined
- Param form complexity exceeds component scope

---

## Evidence Recorded

- **Commit:** 1e8c736 — Cluster 7 modular components
- **Tests:** tests/test_frontend_steps_manual_cards.py (34 source-pattern tests)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2417 passed / 1 skipped / 0 failed
