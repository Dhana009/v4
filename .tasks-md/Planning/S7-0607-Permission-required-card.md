# S7-0607 — Permission Required Card

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0601, Cluster 2

---

## Objective

Render `permission_required` backend events as an interactive card showing:
- Risk level (low/medium/high)
- Action/operation being requested
- Why permission is needed
- Options: Allow Once, Allow for Plan, Deny, Edit Plan (if applicable)

User decision dispatches `permission_decision` command; high-risk actions remain blocked until decision received.

---

## Source Rules

1. **PRD-04-BE-001:** permission_required includes risk_level, action, reason, operation_id
2. **PRD-03-FE-002:** User must explicitly choose allow/deny; no auto-allow
3. **PRD-03-FE-006:** High-risk actions blocked until backend confirmation

---

## Current Known Context

### What exists

- Backend emits permission_required event
- No PermissionCard component

### What gaps exist

- Risk level visual design
- Option mapping (Allow Once vs Allow for Plan)
- permission_decision command structure

---

## Tests First

### Unit Tests

```
test_permission_decision_command_includes_required_fields()
test_high_risk_action_requires_explicit_allow()
```

### Component Tests

```
test_permission_card_displays_risk_level()
test_permission_card_shows_action_and_reason()
test_permission_card_renders_allow_deny_options()
test_permission_card_shows_edit_plan_option_if_available()
```

### Contract Tests

```
test_permission_required_event_includes_risk_and_action()
```

### Negative Tests

```
test_permission_with_missing_risk_level_handled()
test_missing_action_description_safe()
```

### Integration Tests

```
test_permission_required_event_shows_card()
test_permission_decision_command_dispatched()
test_high_risk_blocks_execution_until_decision()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/cards/PermissionCard.jsx`
- **New:** `frontend/src/commands/permission_commands.js`
- **New:** `tests/test_frontend_permission_card.py`

### Forbidden Files

- No execution permission grant logic
- No automatic permission

---

## Implementation Notes

### Approach

1. Permission Card:
   - Risk indicator (color-coded)
   - Action description
   - Reason explanation
   - Button group: Allow Once, Allow for Plan, Deny
   - Optional: Edit Plan button

2. Commands:
   - `permission_decision { run_id, permission_id, decision: "allow_once" | "allow_for_plan" | "deny" }`

3. Blocking:
   - High-risk actions disabled until decision
   - Card prominent and cannot be dismissed

### Key Invariants

- User must explicitly choose
- No auto-allow
- Backend confirms decision acceptance

---

## Acceptance Criteria

- [ ] PermissionCard renders risk level, action, reason
- [ ] All allow/deny options available
- [ ] User cannot dismiss card without decision
- [ ] permission_decision command sent with choice
- [ ] High-risk actions blocked until decision
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/cards/PermissionCard.jsx` exists
- [ ] `tests/test_frontend_permission_card.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Risk level mapping undefined
- Card requires execution permission logic
