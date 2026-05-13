# S7-0604 — Plan Ready Review Card

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0601, Cluster 2

---

## Objective

Render `plan_ready` backend events as a structured review card showing:
- Plan ID and version
- Steps with operation summaries
- Risks and confidence levels
- Expected outcomes
- Confirmation button (disabled until user explicitly confirms)

Frontend must not execute before backend acceptance.

---

## Source Rules

1. **PRD-04-BE-001:** plan_ready includes run_id, plan, steps[], summary, confidence
2. **PRD-03-FE-001:** Plan card shows backend plan structure exactly
3. **PRD-03-FE-006:** User must confirm plan; backend validates before execution

---

## Current Known Context

### What exists

- Backend emits plan_ready event
- Design prototype shows plan card UI
- No production plan card component

### What gaps exist

- No PlanReadyCard component
- No plan version tracking
- No confidence/risk display
- confirm_plan command not tested

---

## Tests First

### Unit Tests

```
test_confirm_plan_command_includes_plan_id_version()
test_confirm_button_disabled_until_user_action()
```

### Component Tests

```
test_plan_card_renders_steps_list()
test_plan_card_shows_confidence_and_risk()
test_plan_card_shows_expected_outcomes()
test_plan_card_displays_plan_id_and_version()
test_confirm_button_visually_prominent()
```

### Contract Tests

```
test_plan_ready_event_includes_plan_id_steps()
test_steps_include_operation_summaries()
```

### Negative Tests

```
test_malformed_steps_rendered_safely()
test_missing_plan_id_rejected()
test_empty_steps_shows_safe_message()
```

### Integration Tests

```
test_plan_ready_event_shows_card()
test_confirm_plan_command_dispatched()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/cards/PlanReadyCard.jsx`
- **New:** `frontend/src/store/plan_reducer.js`
- **New:** `frontend/src/commands/plan_commands.js`
- **New:** `tests/test_frontend_plan_card.py`
- **Modify:** `frontend/src/aw-ide-panel.jsx` (thin wiring only)

### Forbidden Files

- No backend changes
- No execution logic

---

## Implementation Notes

### Approach

1. Define plan state:
   - `{ plan_id, plan_version, steps[], summary, confidence, risks[] }`

2. Create PlanReadyCard:
   - Header: "Plan Ready - Step N/Total"
   - Steps list with operation summaries
   - Confidence indicator
   - Risks section (if applicable)
   - Expected outcomes (if provided)
   - Confirm Plan button (prominent, requires explicit click)

3. Command dispatch:
   - `confirm_plan { run_id, plan_id, plan_version }`

### Key Invariants

- No execution before confirm
- Plan ID and version stable across submission
- Backend decides if plan is executable

---

## Acceptance Criteria

- [ ] PlanReadyCard renders plan from backend event
- [ ] All plan details (steps, risks, expected outcomes) displayed
- [ ] Confirm button requires explicit user action
- [ ] confirm_plan command includes all required fields
- [ ] No browser action before backend acceptance
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/cards/PlanReadyCard.jsx` exists
- [ ] `tests/test_frontend_plan_card.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Plan structure from backend undefined
- Card requires inferring execution readiness
