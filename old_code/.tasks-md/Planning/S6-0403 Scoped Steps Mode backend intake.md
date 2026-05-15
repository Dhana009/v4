# S6-0403 Scoped Steps Mode backend intake

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Tier:** 1 (core)  
**Type:** Feature / API  
**Status:** Planning  
**Owner:** Steps Intake  
**Blocks:** S6-0404  
**Blocked by:** S6-0401  

---

## Purpose

Implement backend intake for structured pending steps from the Steps tab/API. Pending steps with stable step_id, display order, picked element/section context, expected outcome/postcondition, test data references, locator status, and warnings. No frontend visual work, no execution, no plan mutation UI.

---

## Source rules

- Frontend spec: Steps tab supports focused steps, picked element/section, expected outcome/postcondition, test data, locator status, reordering, deleting, duplicating
- Frontend spec: step identity must use stable `step_id`; frontend must not treat display order as identity
- Pending steps come from frontend via API
- Backend must preserve step identity across reorder/delete/duplicate

---

## What it contains

```
- pending steps
- stable step_id
- display order
- picked element/section context
- expected outcome/postcondition
- test data references
- locator status
- warnings
```

---

## What it must NOT contain

```
- no frontend visual work
- no execution
- no plan mutation UI
```

---

## Tests first

### Unit tests

```
- step_id remains stable when order changes
- selected element context preserved
- selected section context preserved
- expected outcome stored as metadata
- test data references stored without raw secrets
```

### Contract tests

```
- frontend display order is not identity
- backend rejects malformed pending step payload
- expected_outcome never becomes assertion target/value by itself
```

### Integration tests

```
- pending steps received from API
- step identity preserved across operations
```

Coverage: **95% for steps_intake module**

---

## Out of scope

- Do not implement frontend UI
- Do not execute steps
- Do not implement plan mutations

---

## Allowed files

```
runtime/steps_intake.py (new)
tests/test_steps_intake.py (new)
Minor edits to:
  - API/backend model if needed
```

---

## Forbidden files

- No frontend code
- No execution logic
- No plan mutation logic

---

## Implementation notes

### Schema (in steps_intake.py or shared contracts)

```
PendingStep:
  - step_id: string (UUID, immutable)
  - display_order: int (mutable)
  - operation_type: enum (click / fill / navigate / assert / etc.)
  - description: string
  - picked_element: optional ElementReference (CSS selector, ARIA, etc.)
  - picked_section: optional SectionReference (landmark, heading, etc.)
  - expected_outcome: string (not an assertion value, just description)
  - postcondition: optional PageStateChange
  - test_data_refs: dict[string, string] (field_name → test_data_key, no secrets)
  - locator_status: enum (clear / ambiguous / missing / validated)
  - warnings: list[string]

PendingStepsPayload:
  - steps: list[PendingStep]
  - request_id: string (links back to journey request)
```

### Approach

1. Create `runtime/steps_intake.py` with:
   - `intake_pending_steps(payload)` → list[ValidatedPendingStep]
   - Validate step_id uniqueness and format
   - Preserve step_id immutability (error if attempt to change)
   - Allow reorder (change display_order)
   - Preserve element/section context
   - Store expected_outcome as metadata (not value)
   - Store test data references (no secrets)
   - Return validated steps or validation errors

2. Create `tests/test_steps_intake.py`:
   - step_id stability across reorder
   - element/section context preserved
   - expected_outcome stored as metadata
   - test data references safe (no secrets)
   - validation rejects malformed payloads
   - display order is mutable

3. Update API/backend if needed:
   - POST endpoint to receive pending steps
   - Each pending step validated through steps_intake
   - Response includes step IDs (so frontend can reference them)

### Key invariants

- step_id is immutable and unique
- display_order is mutable (allows reordering)
- expected_outcome is metadata, not assertion target
- test data references don't leak secrets
- Validation enforces schema

---

## Validation commands

```bash
python -m pytest tests/test_steps_intake.py::test_step_id_stability -v
python -m pytest tests/test_steps_intake.py::test_display_order_mutable -v
python -m pytest tests/test_steps_intake.py::test_context_preserved -v
python -m pytest tests/test_steps_intake.py::test_test_data_safe -v
python -m pytest tests/test_steps_intake.py::test_validation -v
coverage run -m pytest tests/test_steps_intake.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/steps_intake.py` created
- [ ] `tests/test_steps_intake.py` created
- [ ] PendingStep schema defined
- [ ] step_id stable across operations
- [ ] element/section context preserved
- [ ] expected_outcome stored as metadata
- [ ] test data references safe
- [ ] Validation enforced
- [ ] 95% coverage

---

## Stop conditions

- Frontend Steps API contract unclear (clarify in story)
- test data reference format ambiguous (define in story)

---

## Sign-off

- [x] Story is specific (implement steps intake)
- [x] Scope is bounded (intake only, no execution)
- [x] Tests are first
- [x] Blocks S6-0404 (multi-step planning)
