# S7-0710 — Manual Assertion Builder

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0708

---

## Objective

Let users build manual assertion steps in Manual Mode. Assertion types: visible, hidden, enabled, disabled, has text, exact text, has value, checked, url matches, title matches, count equals, table/list contains.

Users select assertion type, fill expected values, add to step list. Backend validates before execution.

---

## Source Rules

1. **PRD-03-FE-006:** Frontend builds step draft; backend validates
2. **PRD-04-BE-001:** add_step command includes assertion_type, expected_value, locator
3. **Cluster 7 strategy:** Manual Mode deterministic first

---

## Tests First

### Component Tests

```
test_assertion_type_dropdown_shows_all_types()
test_has_text_requires_expected_text()
test_exact_text_requires_exact_match()
test_url_matches_requires_pattern()
test_count_equals_requires_number()
test_add_assertion_dispatches_command()
test_required_fields_prevent_submit()
test_unsupported_assertion_shows_gap()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/manual/AssertionBuilder.jsx`
- **New:** `frontend/src/components/manual/AssertionTypeForm.jsx` (polymorphic)
- **Modify:** `frontend/src/commands/step_commands.js`
- **New:** `tests/test_frontend_manual_assertion_builder.py`

### Forbidden Files

- No backend assertion execution
- No local assertion validation

---

## Implementation Notes

1. AssertionBuilder:
   - Assertion type dropdown
   - Conditional param form per type
   - Add button dispatches add_step command

2. Assertion types with required params:
   - visible: locator only
   - hidden: locator only
   - enabled/disabled: locator only
   - has text: locator, text
   - exact text: locator, text
   - has value: locator, value
   - checked: locator only
   - url matches: pattern
   - title matches: pattern
   - count equals: locator, count (number)
   - table/list contains: locator, value

---

## Acceptance Criteria

- [ ] Assertion type selector works
- [ ] Param forms per type
- [ ] Required fields enforced
- [ ] add_step command dispatched
- [ ] Unsupported assertions show disabled reason
- [ ] Backend validation required
- [ ] All tests pass, coverage ≥ 95%

---

## Stop Conditions

- Backend assertion validation structure undefined
- Form complexity exceeds component scope
