# S7-0509 — Live Prop Threading into IDEPanel

**Sprint:** Sprint 7  
**Cluster:** 5  
**Story:** S7-0509  
**Status:** Done  
**Date:** 2026-05-14  

---

## Objective

Thread live backend state from store into IDEPanel components. IDEPanel receives all props from store (plan, steps, interaction_mode, pending_decisions, etc.). Components render backend truth, not static fallback.

After S7-0509:
- IDEPanel connected to store
- Props: plan, pending_steps, recorded_steps, code_preview, interaction_mode, pending_clarification, pending_permission, pending_recovery, pending_recommendations, errors, trace_entries
- Callbacks for user actions: onConfirmPlan, onPermissionDecision, onSkipStep, etc.
- No static fallback content in live mode
- Design/demo mode isolated if retained for reference

---

## Current Context

- IDEPanel receives some props (partial)
- No store connection
- Static demo content may appear

---

## Tests First

### Unit Tests

**Test: IDEPanel props from store**
- Store state → IDEPanel props flow
- Props typed correctly
- No prop mismatch

**Test: Live mode vs demo mode**
- Live mode: props from store
- Demo mode (if retained): props from fixtures
- Modes isolated (don't mix)

### Component Tests

**Test: IDEPanel renders plan from props**
- Store has plan → IDEPanel shows plan
- Store has no plan → IDEPanel shows "no plan" (not static fallback)

**Test: IDEPanel renders steps**
- Store has pending_steps → IDEPanel shows steps list
- Store has recorded_steps → Recorded tab shows recorded steps

**Test: IDEPanel shows mode-specific UI**
- interaction_mode='plan_review' → show plan review card
- interaction_mode='clarification' → show clarification card
- interaction_mode='recovery' → show recovery card

**Test: Callbacks wired**
- User clicks "Confirm Plan" button → onConfirmPlan callback called
- Callback dispatches command via dispatcher

### Integration Tests

**Test: Store update → UI re-render**
- Store emits new state
- IDEPanel receives updated props
- UI reflects new state (React re-render)

**Test: Full flow**
- WebSocket receives plan_ready event
- Store reducer processes event → state updated
- IDEPanel receives new plan prop
- UI shows plan review card
- User clicks confirm
- Callback calls dispatcher
- Command sent to backend

### Negative Tests

**Test: No plan → graceful rendering**
- plan is null
- IDEPanel renders placeholder (not crash)

**Test: Invalid mode → fallback UI**
- interaction_mode is null or unknown
- UI shows default state (not crash)

**Test: No static fallback in live mode**
- Live mode (connected to store)
- Verify no hardcoded demo content shown
- Verify all content from props

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `frontend/src/aw-ide-panel.jsx`
  - Receive props from store (not magic string state)
  - Add callbacks for user actions
  - ≤20 lines of new prop threading

- **Modify:** `frontend/src/main.jsx`
  - Connect IDEPanel to store
  - Pass props and callbacks
  - ≤20 lines

- **New tests:** `tests/test_idePanel_props.py` (or TS test)

### Forbidden Changes

- No new logic in IDEPanel
- No state management in IDEPanel (props only)
- No static demo content in live mode

---

## Acceptance Criteria

✅ **Props threaded correctly:**
- All required props flow from store to IDEPanel
- Callbacks wired for user actions

✅ **Live mode rendering:**
- IDEPanel shows backend truth
- No static fallback in live mode

✅ **Modes functional:**
- plan_review, clarification, recovery, executing modes all render correctly

✅ **Tests passing:**
- Component tests green
- Full flow integration test green
- Regression baseline maintained

✅ **Evidence:**
- IDEPanel receives live props
- Screenshot showing live mode rendering (not demo)
- All callbacks dispatching commands

---

## Stop Conditions

- ❌ Static demo content appears in live mode
- ❌ IDEPanel doesn't receive required props
- ❌ Callback doesn't dispatch command
- ❌ UI crash on null props (should gracefully handle)

---

## Related

- Prerequisite: S7-0501 through S7-0508 (all reducers, dispatcher)
- Final Cluster 5 story

---

## Cluster 5 Complete

After S7-0509, all event store and command dispatcher stories Done.

Cluster 5 closes BUG-S6-FINAL-002 by wiring live backend state into frontend UI.

## Cluster 5 Acceptance Checklist

- [ ] All 9 stories green
- [ ] Event types typed and exported
- [ ] Reducer pure and testable
- [ ] Session_state consumer working
- [ ] All event handlers implemented
- [ ] Command dispatcher typed and validating
- [ ] Stale ID blocking working
- [ ] IDEPanel receiving live props
- [ ] No static demo content in live mode
- [ ] Full flow integration test passing
- [ ] Regression baseline maintained
- [ ] Ready for Cluster 6 (LLM tab UI implementation)

---

## Evidence Recorded

- **Commit (RED):** 65eb6d6 — test_frontend_event_store_handlers.py (10 new RED tests)
- **Commit (GREEN):** 345365e — reducer extension + main.jsx threading
- **Change:** storeState threaded into IDEPanel runtime prop (connected, run_id, phase, plan, pending/recorded steps, code_preview, errors, modes, pending_clarification/permission/recovery/recommendations); createDispatcher imported
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2347 passed / 1 skipped / 0 failed
