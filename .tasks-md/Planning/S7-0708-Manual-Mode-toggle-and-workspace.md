# S7-0708 — Manual Mode Toggle and Workspace

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocks:** S7-0709, S7-0710

---

## Objective

Add Manual Mode as a mode toggle inside Steps tab (not a separate top-level tab). Manual Mode is deterministic/manual-control-first; LLM help is explicit and optional. Same backend recording/code/replay systems work for both LLM Mode and Manual Mode steps.

After S7-0708: Users can toggle between LLM Mode and Manual Mode in Steps tab. Manual Mode workspace shows action/assertion builders.

---

## Source Rules

1. **PRD-03-FE-002:** Manual Mode is deterministic first, not LLM-driven
2. **PRD-03-FE-003:** Same Recorder/Code/Trace systems serve both modes
3. **Cluster 7 strategy:** Manual Mode includes action/assertion builders, element picker, locator validation

---

## Current Known Context

### What exists

- Design prototype shows Manual Mode layouts
- No mode toggle in production

### What gaps exist

- No mode state in store
- No mode toggle UI
- No Manual Mode workspace layout

---

## Tests First

### Unit Tests

```
test_mode_toggle_updates_store()
test_mode_state_persists_across_operations()
```

### Component Tests

```
test_mode_toggle_visible_in_steps_tab()
test_llm_mode_workspace_shows_when_llm_mode_active()
test_manual_mode_workspace_shows_when_manual_mode_active()
test_switching_modes_preserves_backend_state()
```

### Integration Tests

```
test_mode_toggle_updates_ui()
test_manual_mode_does_not_auto_invoke_llm()
```

### Negative Tests (required by GOV-S7-C0-009 and GOV-S7-C0-027)

```
test_invalid_mode_value_rejected()                        # GOV-S7-C0-027 — only "llm"|"manual" accepted
test_mode_switch_mid_run_blocked_or_requires_confirm()    # GOV-S7-C0-001 — backend truth not disrupted
test_mode_toggle_disabled_while_recovery_card_open()      # PRD-03-FE-007 — recovery owns interaction
test_mode_toggle_disabled_while_save_or_load_in_flight()  # PRD-04-CMD-003/004 — no command race
test_mode_switch_does_not_discard_backend_state()         # GOV-S7-C0-001 — run_id, recorded steps preserved
test_manual_mode_does_not_auto_call_llm()                 # PRD-03-FE-002 — Manual Mode deterministic first
test_manual_mode_does_not_locally_mark_step_recorded()    # GOV-S7-C0-001 — recording is backend-owned
test_manual_mode_does_not_locally_mark_code_update()      # GOV-S7-C0-001 — code_update is backend-owned
test_manual_mode_does_not_locally_mark_run_completed()    # GOV-S7-C0-001 — completion is backend-owned
test_mode_state_change_emits_no_backend_command_unless_required()  # PRD-03-FE-007 — frontend mode is UI state only
```

---

## Architectural Invariants (must hold)

- Tests are written first; no implementation commit precedes a failing test commit (GOV-S7-C0-008, GOV-S7-C0-017).
- Backend truth remains authoritative — mode switch never mutates run_id, recorded steps, code_update, or run lifecycle state (GOV-S7-C0-001).
- Frontend mode switch is UI state only. It must not synthesize backend lifecycle truth. A backend command/event is required before any deeper state transition (PRD-03-FE-007, GOV-S7-C0-006).
- Manual Mode never auto-invokes the LLM. LLM help in Manual Mode is explicit, user-initiated, and optional (PRD-03-FE-002).
- Same Recorder/Code/Trace systems serve both modes (PRD-03-FE-003); no Manual Mode-specific recording path.

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/steps/ModeToggle.jsx`
- **New:** `frontend/src/store/mode_reducer.js`
- **Modify:** `frontend/src/components/steps/StepsList.jsx` (conditional rendering)
- **New:** `tests/test_frontend_manual_mode.py`

### Forbidden Files

- No LLM invocation in Manual Mode
- No automatic LLM help

---

## Implementation Notes

1. ModeToggle component:
   - Radio/toggle: "LLM Mode" / "Manual Mode"
   - Update store mode state

2. Mode state in store:
   - `mode: "llm" | "manual"`
   - Persist across operations

3. Conditional rendering:
   - LLM Mode: show chat/plan cards
   - Manual Mode: show action/assertion builders

---

## Acceptance Criteria

- [ ] Mode toggle visible and functional
- [ ] Mode state in store and persisted
- [ ] LLM Mode and Manual Mode workspaces separate
- [ ] No auto-LLM in Manual Mode
- [ ] Switching modes preserves backend state
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] Components created, tests pass
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Mode state conflicts with existing store structure
- Workspace layout requires complex conditional logic
