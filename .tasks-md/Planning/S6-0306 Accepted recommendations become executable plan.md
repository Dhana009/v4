# S6-0306 Accepted recommendations become executable plan

**Sprint:** Sprint 6  
**Cluster:** 3 (Page Intelligence + Recommendation Mode)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Plan Generation  
**Blocks:** S6-0307  
**Blocked by:** S6-0305  

---

## Purpose

Convert user-approved recommendations into a backend-validated plan. Accepted recommendation list, plan draft generation, operation IDs, expected outcomes, locator status, capability checks, and plan_ready only after backend validation. No execution before confirmation, no auto-recording, no code_update.

---

## Source rules

- Accepted recommendations come from S6-0305 recommendation_review state
- Plan schema exists (from S5-012 or earlier)
- Plan must be validated before plan_ready event
- Unaccepted recommendations are never included

---

## What it contains

```
- accepted recommendation list
- plan draft generation
- operation IDs
- expected outcomes
- locator status
- capability checks
- plan_ready only after backend validation
```

---

## What it must NOT contain

```
- no execution before confirmation
- no auto-recording
- no code_update
```

---

## Tests first

### Unit tests

```
- accepted recommendations produce plan children
- removed recommendations are excluded
- reordered recommendations preserve requested order
- unsupported recommendations blocked or marked capability_gap
```

### Contract tests

```
- plan_ready includes accepted recommendation lineage
- old/unaccepted recommendations never execute
- invalid operation type blocked
```

### Integration tests

```
- recommend assertions → accept subset → plan_ready
```

Coverage: **95% for plan generation from recommendations**

---

## Out of scope

- Do not execute plan
- Do not record to code
- Do not implement locator updates

---

## Allowed files

```
runtime/recommendation_to_plan.py (new)
tests/test_recommendation_to_plan.py (new)
Minor edits to:
  - runtime/llm_runtime_controller.py (emit plan_ready)
  - backend plan model if needed
```

---

## Forbidden files

- No execution logic
- No recording logic
- No locator update logic

---

## Implementation notes

### Approach

1. Create `runtime/recommendation_to_plan.py` with:
   - `generate_plan_from_accepted_recommendations(request_id, accepted_ids)` → ExecutablePlan
   - For each accepted recommendation:
     - Create operation with ID
     - Set expected outcome
     - Set locator status (ambiguous if needed)
     - Check capability (error if unsupported)
     - Preserve user order
   - Validate plan:
     - All operations have required fields
     - No unaccepted recommendations included
     - Capability checks pass or marked as gaps
   - Return plan or validation errors

2. Create `tests/test_recommendation_to_plan.py`:
   - Accepted recommendations → plan operations
   - Removed recommendations excluded
   - Order preserved
   - Capability checks enforced
   - Validation passes

3. Update `agent.py` or event handler:
   - Listen for `recommendation_review_completed` event
   - Call `generate_plan_from_accepted_recommendations()`
   - Emit `plan_ready` only if validation passes
   - Emit `plan_invalid` if validation fails

### Key invariants

- Only accepted recommendations become operations
- User order is preserved
- Unaccepted recommendations are never included
- Plan is validated before plan_ready
- No execution before confirmation

---

## Validation commands

```bash
python -m pytest tests/test_recommendation_to_plan.py::test_accepted_becomes_operations -v
python -m pytest tests/test_recommendation_to_plan.py::test_removed_excluded -v
python -m pytest tests/test_recommendation_to_plan.py::test_order_preserved -v
python -m pytest tests/test_recommendation_to_plan.py::test_validation_required -v
coverage run -m pytest tests/test_recommendation_to_plan.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/recommendation_to_plan.py` created
- [ ] `tests/test_recommendation_to_plan.py` created
- [ ] Accepted recommendations become operations
- [ ] Removed recommendations excluded
- [ ] Order preserved
- [ ] Validation enforced
- [ ] Capability checks pass
- [ ] 95% coverage

---

## Stop conditions

- Plan schema unclear (read S5-012 or existing plan code)
- Recommendation state not available (coordinate with S6-0305)

---

## Sign-off

- [x] Story is specific (convert accepted recommendations → plan)
- [x] Scope is bounded (plan draft only, no execution)
- [x] Tests are first
- [x] Blocks S6-0307 (cheap E2E proof)
