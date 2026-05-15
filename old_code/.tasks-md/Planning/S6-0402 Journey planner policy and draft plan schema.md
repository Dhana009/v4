# S6-0402 Journey planner policy and draft plan schema

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Tier:** 1 (core)  
**Type:** Feature / Schema  
**Status:** Planning  
**Owner:** Plan Schema  
**Blocks:** S6-0404, S6-0405  
**Blocked by:** S6-0401  

---

## Purpose

Complete the `journey_planner` output shape. Draft plan schema with steps, child operations, preconditions, postconditions, expected outcomes, required page state, dependencies, required test data, and permission/risk metadata. No execution, no direct recording, no frontend editing UI.

---

## Source rules

- Journey classifier (S6-0401) identifies full journey requests
- Plan schema must map cleanly to executables
- Each browser-changing step must have risk metadata
- Required data may be missing but must be explicit

---

## What it contains

```
- draft plan schema
- steps
- child operations
- preconditions
- postconditions
- expected outcomes
- required page state
- dependencies
- required test data
- permission/risk metadata
- capability gaps
```

---

## What it must NOT contain

```
- no execution
- no direct recording
- no frontend editing UI
```

---

## Tests first

### Unit tests

```
- draft plan requires stable step IDs
- each browser-changing step has risk metadata
- required data may be missing but must be explicit
- unsupported capability becomes capability gap
```

### Contract tests

```
- invalid plan schema retries/fails closed
- no silent missing preconditions for multi-page flow
- no generated fake test data unless policy allows proposal
```

### Integration tests

```
- fake journey planner produces valid draft plan from page intelligence summary
```

Coverage: **95% for journey_planner_contracts module**

---

## Out of scope

- Do not implement frontend editing UI
- Do not execute plans
- Do not generate real test data

---

## Allowed files

```
runtime/journey_planner_contracts.py (new)
tests/test_journey_planner_contracts.py (new)
```

---

## Forbidden files

- No frontend code
- No execution logic
- No data generation beyond schema

---

## Implementation notes

### Schema definition (journey_planner_contracts.py)

```
DraftPlanStep:
  - step_id: string (stable)
  - order: int
  - description: string
  - operation_type: enum (click / fill / navigate / assert / etc.)
  - target: LocatorHint (not final)
  - expected_outcome: string
  - precondition: PageStateRequirement
  - postcondition: PageStateChange
  - test_data_required: list[string] (field names)
  - risk_level: enum (low / medium / high)
  - required_capabilities: list[string]

DraftJourneyPlan:
  - plan_id: string
  - request_id: string (from classification)
  - steps: list[DraftPlanStep]
  - total_steps: int
  - missing_data: list[string] (required fields not provided)
  - capability_gaps: list[string] (unsupported operations)
  - risk_summary: string
  - requires_confirmation: bool
```

### Approach

1. Create `runtime/journey_planner_contracts.py` with:
   - DraftPlanStep, DraftJourneyPlan schema definitions
   - `generate_draft_plan(classification, page_context)` → DraftJourneyPlan
   - For each step in journey:
     - Create step with stable ID
     - Set operation type (click, fill, navigate, assert, etc.)
     - Add expected outcome
     - Set precondition/postcondition
     - Mark required test data
     - Assess risk level
     - Check capabilities
   - Validate: all required fields present or explicitly marked missing
   - Return plan or validation errors

2. Create `tests/test_journey_planner_contracts.py`:
   - Schema compliance
   - Step ID stability
   - Risk metadata present
   - Missing data marked
   - Capability gaps identified
   - Validation enforced

### Key invariants

- Step IDs are stable across reorder/remove
- Risk metadata is explicit (not silent)
- Missing data is explicit (not assumed)
- Capabilities are checked (not silent failures)

---

## Validation commands

```bash
python -m pytest tests/test_journey_planner_contracts.py::test_schema_compliance -v
python -m pytest tests/test_journey_planner_contracts.py::test_step_id_stability -v
python -m pytest tests/test_journey_planner_contracts.py::test_risk_metadata -v
python -m pytest tests/test_journey_planner_contracts.py::test_missing_data_marked -v
python -m pytest tests/test_journey_planner_contracts.py::test_validation -v
coverage run -m pytest tests/test_journey_planner_contracts.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/journey_planner_contracts.py` with schema
- [ ] `tests/test_journey_planner_contracts.py` with tests
- [ ] DraftPlanStep and DraftJourneyPlan defined
- [ ] Schema validation working
- [ ] Risk metadata present
- [ ] Missing data tracked explicitly
- [ ] Capability gaps identified
- [ ] 95% coverage

---

## Stop conditions

- Journey classification not available (coordinate with S6-0401)
- Plan schema incompatible with existing plan model (check S5-012)

---

## Sign-off

- [x] Story is specific (define journey planner schema)
- [x] Scope is bounded (schema only, no execution)
- [x] Tests are first
- [x] Blocks S6-0404/S6-0405 (planning flows)
