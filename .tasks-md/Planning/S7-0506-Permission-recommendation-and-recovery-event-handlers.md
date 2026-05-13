# S7-0506 — Permission, Recommendation, and Recovery Event Handlers

**Sprint:** Sprint 7  
**Cluster:** 5  
**Story:** S7-0506  
**Status:** Done  
**Date:** 2026-05-14  

---

## Objective

Handle decision-point backend events. permission_required, recommendation_ready, recovery_needed events store pending decision state. UI can display cards for user input.

After S7-0506:
- permission_required event → pending_permission state populated
- recommendation_ready event → pending_recommendations[] populated
- recovery_needed event → pending_recovery state populated
- These states used by components to show decision cards

---

## Tests First

### Unit Tests

**Test: Permission required**
- `reducer(state, {type: 'permission_required', payload: {operation, risk_level, reason}})`
- pending_permission populated
- interaction_mode may not change (permission is blocking, not mode change)

**Test: Recommendation ready**
- `recommendation_ready` event → pending_recommendations[] updated

**Test: Recovery needed**
- `recovery_needed` event → pending_recovery populated
- failure_reason and options[] stored
- interaction_mode may become 'recovery'

**Test: Stale decisions ignored**
- permission_required with old run_id
- Ignored or logged (depends on config)

### Negative Tests

**Test: Null options in recovery**
- recovery_needed with null options[]
- Handled safely

**Test: Empty recommendations**
- recommendation_ready with empty recommendations[]
- UI shows "no recommendations available"

---

## Acceptance Criteria

✅ **Decision states captured:**
- permission_required, recommendation_ready, recovery_needed all processed

✅ **State available for UI:**
- Components can access pending_permission, pending_recommendations, pending_recovery

✅ **Options structured:**
- Recovery options include: label, action (retry/skip/stop)
- Recommendations include: label, description

---

## Stop Conditions

- ❌ Decision options not structured properly
- ❌ Stale decisions overwrite fresh ones

---

## Related

- Prerequisite: S7-0502 (reducer)
- Depended on by: S7-0509 (UI threading)

---

## Next Story

→ S7-0507: Typed command dispatcher

---

## Evidence Recorded

- **Commit (RED):** 65eb6d6 — test_frontend_event_store_handlers.py (10 new RED tests)
- **Commit (GREEN):** 345365e — reducer extension + main.jsx threading
- **Change:** permission_required/recommendation_ready/recovery_needed store payloads; recovery_resolved (new EVENT_TYPE) clears pending_recovery only from backend event; empty options safe
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2347 passed / 1 skipped / 0 failed
