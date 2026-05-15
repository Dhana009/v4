# S6-0404 Queued multi-step planning flow

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Multi-step Planning  
**Blocks:** S6-0405, S6-0406  
**Blocked by:** S6-0402, S6-0403  

---

## Purpose

Plan multiple pending steps in order. Queue submitted to planning, step order preserved, dependency warnings, page-state assumptions, plan_ready with multiple steps. No automatic execution, no broad replay, no frontend drag/drop implementation.

---

## Source rules

- Pending steps come from S6-0403 steps intake
- Journey planner schema exists (S6-0402)
- Each step must be planned in order
- Dependencies between steps must be tracked (e.g., "step 2 depends on step 1 completing")

---

## What it contains

```
- queue submitted to planning
- step order preserved
- dependency warnings
- page-state assumptions
- plan_ready with multiple steps
```

---

## What it must NOT contain

```
- no automatic execution
- no broad replay
- no frontend drag/drop implementation
```

---

## Tests first

### Unit tests

```
- queued steps preserve order
- dependency warnings generated when later step requires navigation
- page-state assumptions added to plan
```

### Contract tests

```
- no execution before confirmation
- plan_ready includes stable step IDs
- removed pending step cannot execute
```

### Integration tests

```
- multi-step queue → step_plan_normalizer → plan_ready
```

Coverage: **95% for steps_planner module**

---

## Out of scope

- Do not execute plan
- Do not implement replay
- Do not implement frontend UI

---

## Allowed files

```
runtime/steps_planner.py (new)
tests/test_steps_planner.py (new)
Minor edits to:
  - runtime/step_plan_normalizer.py (receive multi-step queue)
```

---

## Forbidden files

- No execution logic
- No frontend code
- No broad replay implementation

---

## Implementation notes

### Approach

1. Create `runtime/steps_planner.py` with:
   - `plan_step_queue(pending_steps, page_context)` → ExecutablePlan
   - For each pending step in order:
     - Plan the step (locator validation, expected outcome)
     - Track precondition/postcondition
     - Detect dependencies on prior steps (e.g., "previous step navigated to URL")
     - Add page-state assumptions
     - Create operation with stable step ID
   - Validate:
     - All steps have required fields or explicit gaps
     - Step order is preserved
     - No unplanned steps included
   - Emit dependency warnings (e.g., "Step 3 depends on Step 2 navigating to URL")
   - Return plan_ready only if validation passes

2. Create `tests/test_steps_planner.py`:
   - Order preservation
   - Dependency detection
   - Page-state assumptions
   - Validation

3. Update `step_plan_normalizer.py`:
   - Accept multi-step queue input
   - Call `steps_planner.plan_step_queue()`

### Key invariants

- Step order is preserved
- Dependencies are explicit (warnings, not silent)
- Page-state assumptions are tracked
- No execution before confirmation

---

## Validation commands

```bash
python -m pytest tests/test_steps_planner.py::test_order_preserved -v
python -m pytest tests/test_steps_planner.py::test_dependency_warnings -v
python -m pytest tests/test_steps_planner.py::test_page_state_assumptions -v
python -m pytest tests/test_steps_planner.py::test_validation -v
coverage run -m pytest tests/test_steps_planner.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/steps_planner.py` created
- [ ] `tests/test_steps_planner.py` created
- [ ] Order preserved
- [ ] Dependency warnings generated
- [ ] Page-state assumptions tracked
- [ ] Validation enforced
- [ ] plan_ready only on success
- [ ] 95% coverage

---

## Stop conditions

- step_plan_normalizer contract unclear (read existing code)
- Dependency detection too complex (simplify to basic navigation dependencies)

---

## Sign-off

- [x] Story is specific (plan multi-step queue)
- [x] Scope is bounded (planning only, no execution)
- [x] Tests are first
- [x] Blocks S6-0405/S6-0406 (advanced planning features)
