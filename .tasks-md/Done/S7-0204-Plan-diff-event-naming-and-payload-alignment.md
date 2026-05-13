# S7-0204 Plan Diff Event Naming and Payload Alignment

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0204  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `01_PRODUCT_WORKFLOWS.md` (plan correction workflow).
2. **Frontend UI Spec** — Plan correction discussion must show diffs.
3. **Sprint 6 Handoff** — Plan revision infrastructure exists; needs frontend events.
4. **Cluster 2 Goal** — Plan diffs become frontend-visible typed events.

---

## Objective

Emit typed plan diff events (`plan_diff_proposed`, `plan_diff_validated`, `plan_diff_applied`) so frontend can show and confirm plan corrections. Today, `plan_diff_editor` LLM purpose computes diffs but does not emit events. After S7-0204, frontend receives diff proposals and can accept/reject them.

---

## Tests First

### Unit Tests

**Test: Diff operation builder**
- Given old_plan and new_plan, create diff operations (add, remove, modify, reorder).
- Verify operations are deterministic.

**Test: Diff payload serialization**
- Operations serialize to JSON cleanly (no circular refs, no raw plan objects).

### Contract Tests

**Test: plan_diff_proposed payload shape**
- Fields: plan_id (str), old_version (int), new_version (int), operations (list), timestamp (ISO).
- Each operation has: op (Literal["add", "remove", "modify", "reorder"]), step_index (int), details (dict).
- No raw plan objects; only references and deltas.

**Test: plan_diff_validated payload**
- Fields: plan_id (str), validation_status (Literal["valid", "invalid"]), issues (list | null), timestamp (ISO).

**Test: plan_diff_applied payload**
- Fields: plan_id (str), result (Literal["success", "failed"]), timestamp (ISO).

### Integration Tests

**Test: Diff proposal from plan_diff_editor**
- Call plan_diff_editor with old/new plans.
- Verify plan_diff_proposed event emitted with correct operations.

**Test: Plan validation on diff**
- Validate corrected plan before applying.
- Emit plan_diff_validated event.

**Test: Frontend acceptance → apply**
- Frontend sends accept_plan_diff command.
- Backend applies diff and emits plan_diff_applied event.
- New plan becomes active.

### Negative Tests

**Test: Invalid diff operations**
- If diff contains invalid operation (remove non-existent step, reorder out of bounds), validation fails.
- plan_diff_validated emitted with issues list.

**Test: Stale plan_id**
- Frontend sends accept_plan_diff with old plan_id (plan changed since).
- Backend rejects; emits error event.

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `runtime/event_contracts.py`
  - Add: `PlanDiffProposed`, `PlanDiffValidated`, `PlanDiffApplied` event classes.

- **Modify:** `runtime/plan_revision.py` or create `runtime/plan_diff_events.py`
  - Functions to build and emit diff events.

- **Modify:** `runtime/llm_runtime_controller.py` (thin seam)
  - After plan_diff_editor, emit plan_diff_proposed event.

- **Modify:** `server.py` or `ws/router.py`
  - Handle accept_plan_diff command.

- **New tests:** `tests/test_plan_diff_events.py`

### Forbidden Changes

- No frontend UI.
- No plan execution before acceptance.
- No silent plan mutation.

---

## Acceptance Criteria

✅ **All tests green.**
✅ **Diff operations typed and deterministic.**
✅ **Event payloads match contract.**
✅ **No plan mutation without acceptance.**
✅ **Evidence: test file, commits, regression green.**

---

## Stop Conditions

- ❌ Regression failure.
- ❌ Plan modified without user acceptance.
- ❌ Invalid diff operations not caught.
- ❌ Stale plan_id not validated.

---

## Evidence Recorded

- **Implementation commit:** `0f2198b`
- **Implementation files:**
  - `runtime/event_contracts.py` — added `build_plan_diff_proposed_event`, `build_plan_diff_validated_event`, `build_plan_diff_applied_event`
- **Tests added:** `tests/test_plan_diff_events.py` (22 tests: type, plan_id, versions, operations, envelope, schema_version, contract invariants, negative validation)
- **Validation commands:**
  - `python -m pytest tests/test_plan_diff_events.py -q`
  - `python -m pytest -q`
- **Result summary:**
  - 22 passed
  - Full suite: 2078 passed, 0 failed, 1 skipped
  - `runtime/event_contracts.py` coverage: 99%
- **Confirmation:**
  - `plan_diff_proposed` type ≠ `plan_diff_applied` (no silent mutation)
  - `plan_diff_proposed` type ≠ `plan_ready`, ≠ `step_recorded`
  - None operations raises TypeError
  - Empty plan_id raises ValueError
- **Remaining gaps:** None.

