# S6-0104 Planning and recommendation purpose policies

**Sprint:** Sprint 6  
**Cluster:** 1 (LLM Runtime Purpose Coverage)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Runtime Policy  
**Blocks:** S6-0105, S6-0106, S6-0107  
**Blocked by:** S6-0103  

---

## Purpose

Complete policy for 3 critical planning/recommendation purposes: page_validation_recommender, journey_planner, step_plan_normalizer. These purposes drive multi-step flows and plan discussion. Cannot expose browser-changing tools.

---

## Source rules

- Runtime Policy Spec: planning purposes have no browser-changing tools
- Runtime Policy Spec: page_validation_recommender gets page intelligence summary only
- Runtime Policy Spec: journey_planner marks missing data instead of inventing
- Runtime Policy Spec: step_plan_normalizer preserves stable step IDs
- S5-013 convergence behavior must remain unchanged
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/llm_purpose_registry.py` — registry (from S6-0102)
- `runtime/llm_purpose_policy.py` — 4 low-risk purposes (from S6-0103)
- `tests/test_planning_convergence_contract.py` — convergence tests (must not break)
- `tests/test_page_intelligence_fake_integration.py` — page intelligence tests

### What gaps exist

- No policy for page_validation_recommender (new in Phase 3)
- No policy for journey_planner (new in Phase 4)
- No explicit policy for step_plan_normalizer (exists but needs formal policy)
- No tests for multi-step planning output schema
- Convergence behavior assumed but not explicitly in policy

---

## Desired behavior

### High-level expectation

After S6-0104:

1. 3 planning purposes have explicit policies
2. All have strict schema (no prose plans)
3. All forbid browser-changing tools
4. step_plan_normalizer enforces S5-013 convergence constraints
5. Tests verify schema + no tool exposure

### Purpose details

**page_validation_recommender**
- Input: page intelligence summary
- Output: list of {element, recommendation, priority}
- Schema: structured list, no prose
- Validator: validates each recommendation structure
- Tools: none (LLM, inspection/read-only)
- Fallback: ask_user for clarification

**journey_planner**
- Input: user intent + available pages + requirements
- Output: list of {page_id, action, expected_result, ambiguities}
- Schema: step list with ambiguity markers
- Validator: marks unknown data as ambiguity, never invents
- Tools: none (LLM, inspection/read-only)
- Fallback: ask_user for missing required data

**step_plan_normalizer**
- Input: user intent + page state + locator candidates
- Output: execution plan with stable step IDs
- Schema: structured plan (from S5-013)
- Validator: enforces step ID stability, required fields
- Tools: LLM, inspection/read-only, ask_user, needs_more_context (from convergence)
- Constraint: convergence narrowing still applies (6 tool set → 2 tool set)
- Fallback: ask_user

---

## Out of scope

- Do not implement live Page Intelligence invocation (comes in Cluster 3)
- Do not change S5-013 convergence narrowing behavior
- Do not build frontend UI for journey/recommendation display
- Do not run paid LLM

---

## Allowed files

- `runtime/llm_purpose_policy.py` (modify: add 3 purpose policies)
- `runtime/llm_purpose_registry.py` (modify: add to registry)
- `runtime/planning_purpose_validator.py` (new, if modular)
- `tests/test_planning_purpose_policies.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ S5-013 convergence tests (read-only)
- ✗ frontend/
- ✗ Page Intelligence live invocation (comes later)

---

## Tests first

### Unit tests

- `test_page_validation_recommender_schema_valid()`
- `test_page_validation_recommender_forbids_tools()`
- `test_journey_planner_marks_missing_data_as_ambiguity()`
- `test_journey_planner_forbids_invention()`
- `test_journey_planner_forbids_tools()`
- `test_step_plan_normalizer_preserves_step_ids()`
- `test_step_plan_normalizer_schema_matches_s5_013()`
- `test_step_plan_normalizer_forbids_browser_changing_tools()`

### Contract tests

- `test_page_validation_recommender_policy_in_registry()`
- `test_journey_planner_policy_in_registry()`
- `test_step_plan_normalizer_policy_in_registry()`
- `test_convergence_narrowing_still_applies_to_normalizer()`
- `test_s5_013_convergence_contract_tests_still_pass()`

File: `tests/test_planning_purpose_policies.py`

---

## Implementation notes

### Approach

1. Create policy dict for each 3 purposes
2. Define schema for each:
   - page_validation_recommender: list of recommendation objects
   - journey_planner: list of journey step objects with ambiguity field
   - step_plan_normalizer: execution plan (reuse from S5)
3. Create validators:
   - Recommend: each recommendation has element, recommendation, priority
   - Journey: each step has page_id, action, expected_result, ambiguities list
   - Normalizer: step IDs stable, all required fields present
4. Add to registry
5. Write 10+ tests
6. Verify S5-013 convergence tests still pass

### Key invariants

- Planning purposes have zero browser-changing tools
- Journey planner never invents missing data (marks as ambiguity)
- step_plan_normalizer preserves S5-013 constraints (no convergence change)
- All schemas are strict (fail on prose)

---

## Coverage requirement

95% for new purpose validators.

---

## Validation commands

```bash
python -m pytest tests/test_planning_purpose_policies.py -q
python -m pytest tests/test_planning_convergence_contract.py -q  # Must pass
python -c "
from runtime.llm_purpose_registry import PURPOSE_REGISTRY
for p in ['page_validation_recommender', 'journey_planner', 'step_plan_normalizer']:
  print(f'{p}: tools={len(PURPOSE_REGISTRY.get(p).tool_policy)}')
"
```

---

## Artifact/evidence requirement

- [ ] 3 planning purpose policies in registry
- [ ] Schema for each purpose (structured, no prose)
- [ ] Validators for each (strictly typed)
- [ ] 10+ tests passing
- [ ] S5-013 convergence tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references planning purposes

---

## Stop conditions

- Convergence tests fail (cannot proceed)
- Schema conflicts with S5-013 plan structure
- Cannot define clear "ambiguity" markers for journey planner
- Coverage below 95%

---

## Sign-off

- [x] Story focused (3 planning purposes)
- [x] Tests verify no tool exposure
- [x] S5-013 behavior preserved
- [x] Convergence narrowing not changed
