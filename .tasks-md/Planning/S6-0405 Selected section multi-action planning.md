# S6-0405 Selected section multi-action planning

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Section Planning  
**Blocks:** S6-0406  
**Blocked by:** S6-0404  

---

## Purpose

Support selected section intent becoming one parent step with multiple child operations. Selected section summary, multi-action decomposition, parent step, child operations/checks, ordered plan review, and locator validation requirements. No recording unless execution later succeeds, no code_update in planning phase.

---

## Source rules

- Selected section comes from user picking a UI section in frontend
- One parent step with multiple child operations (e.g., "validate section and click CTA")
- Scenario spec: user asks agent to reduce thinking effort for section validation and related actions
- Child operations must preserve user intent order

---

## What it contains

```
- selected section summary
- multi-action decomposition
- parent step
- child operations/checks
- ordered plan review
- locator validation requirements
```

---

## What it must NOT contain

```
- no recording unless execution later succeeds
- no code_update in planning phase
```

---

## Tests first

### Unit tests

```
- broad section intent decomposes into child operations
- child operations preserve user intent order
- assertion then click ordering can be represented
```

### Contract tests

```
- one parent step with multiple children
- no child execution before confirmation
- invalid/ambiguous child target asks clarification
```

### Integration tests

```
- selected section + "validate this section and click CTA" → plan_ready with assert + click children
```

Coverage: **95% for section_planner module**

---

## Out of scope

- Do not execute children
- Do not implement replay
- Do not implement frontend UI for section selection

---

## Allowed files

```
runtime/section_planner.py or updates to steps_planner.py (new logic)
tests/test_section_planner.py (new)
```

---

## Forbidden files

- No execution logic
- No frontend code
- No recording logic

---

## Implementation notes

### Schema (extends DraftPlanStep)

```
ParentStep:
  - step_id: string
  - operation_type: enum (section_validation / section_action / etc.)
  - description: string
  - selected_section: SectionReference
  - child_operations: list[ChildOperation]

ChildOperation:
  - operation_id: string (stable, unique within parent)
  - order_in_parent: int
  - operation_type: enum (assert / click / fill / etc.)
  - target: LocatorHint
  - expected_value: optional
  - postcondition: optional PageStateChange
```

### Approach

1. Create or extend planning logic with:
   - `plan_section_intent(section_context, intent_description)` → ParentStep with ChildOperations
   - Parse intent (e.g., "validate section and click CTA")
   - Decompose into operations:
     - Assertion: check section is visible
     - Validation: check required fields present
     - Action: click CTA
   - Create parent step with child operations
   - Preserve order (assertions before action)
   - Validate child operations

2. Create `tests/test_section_planner.py`:
   - Intent decomposition
   - Child operation order
   - Locator validation for children
   - Parent-child relationship

### Key invariants

- One parent step contains all children
- Child operations preserve intent order
- No execution before confirmation
- Invalid children ask clarification

---

## Validation commands

```bash
python -m pytest tests/test_section_planner.py::test_intent_decomposition -v
python -m pytest tests/test_section_planner.py::test_child_order -v
python -m pytest tests/test_section_planner.py::test_validation -v
coverage run -m pytest tests/test_section_planner.py
```

---

## Artifact/evidence requirement

- [ ] Section planning logic created
- [ ] `tests/test_section_planner.py` created
- [ ] ParentStep with ChildOperations working
- [ ] Intent decomposition working
- [ ] Child order preserved
- [ ] Validation enforced
- [ ] 95% coverage

---

## Stop conditions

- Section reference format unclear (define in story)
- Intent parsing too complex (simplify patterns)

---

## Sign-off

- [x] Story is specific (support section multi-action planning)
- [x] Scope is bounded (planning only, no execution)
- [x] Tests are first
- [x] Blocks S6-0406 (page-state model)
