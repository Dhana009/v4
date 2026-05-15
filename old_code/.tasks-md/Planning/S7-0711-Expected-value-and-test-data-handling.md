# S7-0711 — Expected Value and Test Data Handling

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 2  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocked by:** S7-0709, S7-0710

---

## Objective

Handle expected_outcome and test data references safely. Expected values are metadata until backend validates/executes. Test data refs shown without raw secret values. Missing test data blocks run with reason shown.

---

## Source Rules

1. **PRD-03-FE-006:** Expected outcome metadata; backend validates
2. **PRD-05-CODEGEN:** Test data refs managed safely; secrets redacted
3. **Cluster 7 strategy:** Test data upload/reference uses typed command

---

## Current Known Context

### What exists

- Backend step recording includes expected_outcome field
- Test data structure undefined

### What gaps exist

- No expected outcome input in step forms
- No test data reference display
- No secret redaction UI

---

## Tests First

### Component Tests

```
test_expected_outcome_field_optional()
test_test_data_refs_not_showing_raw_secrets()
test_missing_test_data_blocks_run()
test_upload_file_permission_respected()
```

---

## Implementation Boundaries

### Allowed Files

- **Modify:** Step edit forms (add expected_outcome field)
- **New:** `frontend/src/components/steps/TestDataReference.jsx`
- **New:** `tests/test_frontend_test_data_handling.py`

### Forbidden Files

- No sensitive value exposure
- No test data generation

---

## Acceptance Criteria

- [ ] Expected outcome input available (optional)
- [ ] Test data refs shown safely (secrets redacted)
- [ ] Missing data blocks with reason
- [ ] Upload permission respected
- [ ] All tests pass

---

## Stop Conditions

- Test data structure from backend undefined
- Secret redaction rules unclear

---

## Evidence Recorded

- **Commit:** 1e8c736 — Cluster 7 modular components
- **Tests:** tests/test_frontend_steps_manual_cards.py (34 source-pattern tests)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2417 passed / 1 skipped / 0 failed
