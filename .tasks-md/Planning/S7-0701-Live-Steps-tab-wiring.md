# S7-0701 — Live Steps Tab Wiring

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocks:** S7-0702, S7-0703, S7-0704, S7-0705, S7-0706, S7-0707, S7-0708, S7-0709, S7-0710, S7-0711, S7-0712  
**Blocked by:** Cluster 6

---

## Objective

Replace static mock steps in Steps tab with live-rendered steps from backend/transport state. Frontend renders pendingSteps from store without demo content. Steps update as backend emits step_validating, step_executing, step_recorded events.

Today: Steps tab shows static mock data.
After S7-0701: Steps tab renders real pending steps from backend/store, handles empty state, updates on backend events.

---

## Source Rules

1. **PRD-03-FE-001:** Frontend renders typed backend events and state only
2. **PRD-04-BE-001:** Backend owns step lifecycle truth
3. **PRD-03-FE-003:** Empty state shown when no steps; no demo content in live mode

---

## Current Known Context

### What exists

- Design prototype shows step list layout
- Backend has pendingSteps state
- No production StepsList component
- No steps reducer

### What gaps exist

- No steps reducer (state slice)
- No StepsList component
- No step item render logic
- Static mock data still appears

### Test status

- No step rendering tests exist

---

## Tests First

### Unit Tests

```
test_steps_reducer_initializes_empty()
test_steps_reducer_receives_pending_steps_from_backend()
test_steps_reducer_updates_step_status_on_event()
test_steps_reducer_handles_step_execution()
test_steps_reducer_handles_step_recording()
test_step_ids_remain_stable()
```

### Component Tests

```
test_steps_list_renders_empty_when_no_steps()
test_steps_list_renders_pending_steps()
test_no_demo_content_in_live_mode()
test_step_status_indicators_show()
test_step_edit_controls_visible()
```

### Integration Tests

```
test_pending_steps_from_backend_appear_in_steps_list()
test_step_executing_event_updates_step_status()
test_step_recorded_event_updates_step_display()
```

### Negative Tests

```
test_malformed_step_data_handled_safely()
test_missing_step_id_rejected()
test_null_steps_array_shows_empty_state()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/steps/StepsList.jsx`
- **New:** `frontend/src/components/steps/StepItem.jsx`
- **New:** `frontend/src/store/steps_reducer.js`
- **New:** `frontend/src/store/steps.js` (actions/selectors)
- **New:** `tests/test_frontend_steps_rendering.py`
- **Modify:** `frontend/src/aw-ide-panel.jsx` (thin wiring)

### Forbidden Files

- No backend changes
- No demo data hardcoding

---

## Implementation Notes

### Approach

1. Create steps reducer:
   - State: `{ steps[], selectedStepIds[], mode: "view" | "edit" }`
   - Actions: SET_STEPS, UPDATE_STEP_STATUS, SELECT_STEP
   - Handle run_started, step_validating, step_executing, step_recorded events

2. Create StepsList component:
   - Map steps[] to StepItem components
   - Show empty state if no steps
   - No demo content

3. Create StepItem component:
   - Step summary (action, target)
   - Status indicator (draft, validating, executing, recorded, failed)
   - Edit button (S7-0702)
   - Select checkbox (for run_selected)

4. Wire to transport:
   - Listen for step_* events
   - Dispatch UPDATE_STEP_STATUS on events

### Key Invariants

- Empty state when no steps
- No demo content in live mode
- Step status from backend events, not inferred

---

## Acceptance Criteria

- [ ] StepsList renders real steps from backend state
- [ ] Empty state shown when no steps (no demo)
- [ ] Step status updated on backend events
- [ ] Step IDs stable across renders
- [ ] Edit controls visible but disabled (S7-0702 enables)
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/steps/StepsList.jsx` exists
- [ ] `frontend/src/store/steps_reducer.js` exists
- [ ] `tests/test_frontend_steps_rendering.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Backend step structure undefined
- Steps reducer conflicts with store architecture
- Demo content cannot be removed without breaking other components
