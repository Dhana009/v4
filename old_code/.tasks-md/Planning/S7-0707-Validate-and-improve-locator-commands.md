# S7-0707 — Validate and Improve Locator Commands

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocked by:** S7-0706

---

## Objective

Dispatch validate_locator and improve_locator commands from step edit forms. Users can validate a locator against live page or request LLM improvement. Backend returns validation result or improved locator; frontend does not validate locally.

---

## Source Rules

1. **PRD-04-BE-001:** validate_locator requires step_id, operation_id, locator
2. **PRD-03-FE-006:** Backend validates; frontend does not
3. **PRD-03-FE-001:** Frontend sends typed commands only

---

## Tests First

### Unit Tests

```
test_validate_locator_command_includes_all_ids()
test_improve_locator_sends_user_hint()
test_stale_locator_update_blocked()
```

### Component Tests

```
test_validate_button_visible_in_edit_form()
test_improve_button_visible_in_edit_form()
test_validation_result_updates_form()
test_disabled_when_backend_unavailable()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/commands/locator_commands.js` (extend)
- **Modify:** Edit forms (add Validate/Improve buttons)
- **New:** `tests/test_frontend_locator_commands.py`

### Forbidden Files

- No local locator validation
- No LLM invocation directly

---

## Acceptance Criteria

- [ ] Validate button dispatches command
- [ ] Improve button sends user hint
- [ ] Validation result updates form
- [ ] Disabled state shown when unavailable
- [ ] No local validation
- [ ] All tests pass, coverage ≥ 95%

---

## Stop Conditions

- Backend locator validation structure undefined
- LLM improvement requires direct model invocation

---

## Evidence Recorded

- **Commit:** 1e8c736 — Cluster 7 modular components
- **Tests:** tests/test_frontend_steps_manual_cards.py (34 source-pattern tests)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2417 passed / 1 skipped / 0 failed
