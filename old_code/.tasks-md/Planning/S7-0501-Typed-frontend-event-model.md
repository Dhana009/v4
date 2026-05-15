# S7-0501 — Typed Frontend Event Model

**Sprint:** Sprint 7  
**Cluster:** 5  
**Story:** S7-0501  
**Status:** Done  
**Date:** 2026-05-14  

---

## Source Rules

1. **PRD v2.3** — `04_BACKEND_EVENT_CONTRACT.md` — event taxonomy
2. **Frontend UI Spec** — interaction modes driven by events
3. **Cluster 5 Goal** — typed, frontend-visible state

---

## Objective

Define typed frontend event model. Each backend event type has a TypeScript/JavaScript type definition. Frontend can import and use these types to validate events before reducing state.

After S7-0501:
- TypeScript interfaces for all backend event types
- Events: session_state, run_started, plan_ready, clarification_needed, recommendation_ready, permission_required, step_validating/executing/failed/skipped, recovery_needed, code_update, run_completed, runtime_rejected, etc.
- Optional fields clearly marked
- Event type discriminator union type
- Importable by store and components

---

## Current Context

- No typed event model in frontend
- Events handled as loose objects
- No validation

---

## Tests First

### Unit Tests

**Test: Event type definitions exist**
- Import EventType types (session_state, run_started, plan_ready, etc.)
- Verify types defined (TypeScript interfaces or JSDoc)
- Verify discriminator field: `type`

**Test: Event payload validation**
- TypeScript compilation checks types
- Invalid payload rejected (type mismatch)
- Valid payload accepted

**Test: Optional fields**
- Fields like `error_context` marked optional
- Code can safely check for undefined

**Test: Event discriminator union**
- `event: RunStarted | PlanReady | Clarification | ...`
- TypeScript can narrow union based on type field

### Contract Tests

**Test: Event payload shapes match backend**
- SessionState includes: run_id, plan_id, pending_steps[], recorded_steps[], phase
- RunStarted includes: run_id, timestamp
- PlanReady includes: plan_id, plan, version, timestamp
- ClarificationNeeded includes: question_id, question, options[], target_step
- All required fields present

**Test: Payload serialization**
- Event payload serializable to JSON
- Roundtrip: JSON → object → JSON matches

### Integration Tests

**Test: Event types imported and used**
- Import types in store module
- Use types to annotate reducer functions
- TypeScript compilation succeeds

---

## Implementation Boundaries

### Allowed Changes

- **New file:** `frontend/src/types/events.ts` or `frontend/src/types/events.d.ts`
  - Export: type definitions for all event types
  - Use TypeScript or JSDoc for type safety
  - Max 300 lines

- **New tests:** `tests/test_frontend_event_types.py` (or TS test file)

- **No runtime code:** This is types-only story

### Forbidden Changes

- No state logic
- No component changes
- No backend changes

---

## Acceptance Criteria

✅ **Event types defined:**
- All event types from backend documented
- TypeScript interfaces or JSDoc
- Optional fields marked

✅ **Type exports available:**
- Importable from frontend/src/types/events
- No circular dependencies

✅ **Validation possible:**
- TypeScript can check event payloads
- Invalid payloads caught at compile-time

✅ **Tests passing:**
- Type definitions valid
- Serialization works
- Regression baseline maintained

---

## Stop Conditions

- ❌ Event type missing from model
- ❌ Required field marked optional (or vice versa)
- ❌ TypeScript errors on valid events

---

## Related

- Prerequisite: None (types first)
- Depended on by: S7-0502 (reducer)

---

## Next Story

→ S7-0502: Frontend reducer and event store

---

## Evidence Recorded

- **Commit (RED):** 82bbeb1 — test_frontend_event_store.py (54 tests, all RED)
- **Commit (GREEN):** c1084ac — types.js: EVENT_TYPES, COMMAND_TYPES fully implemented
- **File:** `frontend/src/store/types.js` — exports EVENT_TYPES (17 event strings) and COMMAND_TYPES (7 command strings)
- **Regression:** 2321 passed / 1 skipped / 0 failed
