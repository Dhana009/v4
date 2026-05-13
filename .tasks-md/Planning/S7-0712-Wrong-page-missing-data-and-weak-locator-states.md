# S7-0712 — Wrong Page, Missing Data, and Weak Locator States

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 2  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0701, S7-0706, S7-0707

---

## Objective

Render common blocked states in Steps/Manual Mode with clear reasons and legal next actions:
- Wrong page precondition: show required page URL vs. current page
- Missing test data: show required reference, upload option
- Weak locator: show confidence warning, improve options

Blocked steps cannot run; user sees why and what to do.

---

## Source Rules

1. **PRD-03-FE-002:** Frontend shows blocked reasons, not silent failures
2. **PRD-03-FE-006:** Frontend shows legal next actions per blocked state
3. **Cluster 7 strategy:** No silent navigation/repair without user/backend command

---

## Current Known Context

### What exists

- Design prototype shows error states
- No production blocked state components
- Reasons structure undefined

---

## What gaps exist

- No wrong page state display
- No missing data indicator
- No weak locator warning
- No state machine for blocked reasons

---

## Tests First

### Component Tests

```
test_wrong_page_shows_required_vs_current()
test_missing_data_shows_required_ref()
test_weak_locator_shows_confidence()
test_blocked_step_cannot_run()
test_next_actions_shown_per_blocked_state()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/steps/BlockedStateDisplay.jsx`
- **New:** `tests/test_frontend_blocked_states.py`
- **Modify:** Step display (integrate blocked state)

### Forbidden Files

- No automatic navigation/repair
- No silent fallback

---

## Implementation Notes

1. Blocked state types:
   - `{ type: "wrong_page", required_url, current_url }`
   - `{ type: "missing_data", required_ref }`
   - `{ type: "weak_locator", confidence }`

2. Display:
   - Show reason clearly
   - Show current vs. required (if applicable)
   - Show next legal actions

---

## Acceptance Criteria

- [ ] Wrong page state shown with URLs
- [ ] Missing data shown with ref
- [ ] Weak locator shown with confidence
- [ ] Blocked steps disabled
- [ ] Legal next actions visible
- [ ] No silent repairs
- [ ] All tests pass

---

## Stop Conditions

- Blocked state structure from backend undefined
- Automatic repair logic required
