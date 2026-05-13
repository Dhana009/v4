# S7-0706 — Locator Candidate Display

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0704

---

## Objective

Show locator candidates in step edit forms with validation count, confidence/risk labels. Candidates are from backend locator_specialist or deterministic extraction. User can choose candidate; backend validates before use.

---

## Source Rules

1. **PRD-04-BE-001:** locator_candidates_ready includes candidates[{id, label, scope, confidence, risk}]
2. **PRD-03-FE-001:** Candidates shown exactly as backend provides
3. **PRD-03-FE-006:** Backend validation required

---

## Tests First

### Component Tests

```
test_locator_candidates_render_with_labels()
test_confidence_and_risk_displayed()
test_candidate_selection_state()
test_duplicate_candidates_show_blocked()
test_no_candidates_shows_message()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/locator/CandidateList.jsx`
- **New:** `tests/test_frontend_locator_candidates.py`
- **Modify:** Edit forms (add candidate selector)

### Forbidden Files

- No locator validation logic
- No browser testing

---

## Acceptance Criteria

- [ ] Candidates render from backend event
- [ ] Confidence/risk labels shown
- [ ] User can select candidate
- [ ] Duplicate candidates detected
- [ ] All tests pass, coverage ≥ 95%

---

## Stop Conditions

- Candidate structure from backend undefined
- Duplicate detection requires complex logic
