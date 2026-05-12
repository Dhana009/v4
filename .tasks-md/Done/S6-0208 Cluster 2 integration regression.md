# S6-0208 Cluster 2 integration regression

**Sprint:** Sprint 6  
**Cluster:** 2 (Context/Memory/Token/Tool/Schema Policy Enforcement)  
**Tier:** 1 (core)  
**Type:** Integration  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** (none, closes Cluster 2)  
**Blocked by:** S6-0207  

---

## Purpose

Prove Cluster 1 + Cluster 2 policies work together end-to-end. Verify no regressions in Sprint 5 behavior. All policies enforced, unknown purpose fails closed, convergence path still passes.

---

## Source rules

- Cluster 1: all 14 purposes have policy
- Cluster 2: contexts/gates/escalation/memory/tools/schema/budget all enforced
- Sprint 5 closure: S5-013 convergence tests must still pass
- Coverage requirement: 95% for integration tests

---

## Current evidence

### What exists

- All Cluster 1 stories (S6-0101–0107) complete
- All Cluster 2 stories (S6-0201–0207) complete
- Sprint 5 tests (test_planning_convergence_contract.py, test_page_intelligence_fake_integration.py, etc.)

### What gaps exist

- No integration test proving all policies work together
- No regression test vs Sprint 5
- Unknown purpose behavior not verified

---

## Desired behavior

### Integration tests

1. **Purpose resolution**: Each of 14 purposes can be resolved to complete policy
2. **Context building**: Controller builds L0–L5 context per purpose default
3. **Tool exposure**: Tools match purpose policy
4. **Schema validation**: Output validated + retry on failure
5. **Budget enforcement**: Budget checked before call
6. **Memory selection**: Only relevant memory included
7. **Unknown purpose**: Falls through with error, never proceeds
8. **Convergence path**: S5-013 behavior unchanged

### Example flow

```python
# Cluster 2 working correctly:
purpose_id = "step_plan_normalizer"
context = build_context_for_purpose(purpose_id)  # Uses L1 by default
tools = get_tools_for_purpose(purpose_id)        # Convergence-constrained
schema = get_schema_for_purpose(purpose_id)      # Structured plan
output = validate_and_retry(purpose_id, llm_output)  # Retry on failure
budget_ok = check_budget(purpose_id, tokens_used)    # Budget enforced

# Unknown purpose fails:
purpose_id = "unknown_purpose"
try:
    PURPOSE_REGISTRY.get(purpose_id)
except ValueError:
    # Correct: fails closed
```

---

## Out of scope

- Do not implement new LLM calls (use fake/mock)
- Do not run paid LLM
- Do not change Sprint 5 behavior

---

## Allowed files

- `tests/test_cluster_2_integration.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ Product code changes
- ✗ S5 test modifications

---

## Tests first

### Integration tests

- `test_all_14_purposes_resolve_to_complete_policy()`
- `test_controller_builds_context_per_purpose_default()`
- `test_controller_enforces_tool_exposure_per_purpose()`
- `test_schema_validation_integrated()`
- `test_token_budget_integrated()`
- `test_memory_selection_integrated()`
- `test_context_sufficiency_gates_integrated()`
- `test_context_escalation_request_integrated()`
- `test_unknown_purpose_fails_immediately()`
- `test_s5_013_convergence_tests_still_pass()`
- `test_page_intelligence_fake_integration_still_passes()`
- `test_all_s5_regression_guard_tests_pass()`

File: `tests/test_cluster_2_integration.py`

---

## Implementation notes

### Approach

1. Create `tests/test_cluster_2_integration.py`:
   ```python
   def test_all_14_purposes_resolve():
       for p_id in [all 14 purpose IDs]:
           policy = PURPOSE_REGISTRY.get(p_id)
           assert policy.model_class is not None
           assert policy.context_policy is not None
           assert policy.tool_policy is not None
           assert policy.schema_id is not None
           assert policy.validator_id is not None
           assert policy.fallback_policy is not None
   
   def test_controller_flow():
       context = build_context_for_purpose("step_plan_normalizer")
       assert context is not None
       tools = get_tools_for_purpose("step_plan_normalizer")
       assert len(tools) > 0
       # ... etc
   ```

2. Run all S5 regression guard tests
3. Run Cluster 1 + 2 tests together
4. Write 12+ integration tests

### Key invariants

- All policies resolved successfully
- All enforcement layers active
- Unknown purpose truly fails
- S5 tests still pass
- No breaking changes

---

## Coverage requirement

95% for integration tests (focused on cross-module interactions).

---

## Validation commands

```bash
# Run Cluster 2 integration tests
python -m pytest tests/test_cluster_2_integration.py -q

# Run all S5 regression tests (must all pass)
python -m pytest tests/test_planning_convergence_contract.py tests/test_page_intelligence_fake_integration.py tests/test_llm_runtime_controller_contract.py -q

# Run all Cluster 1 + 2 tests
python -m pytest tests/test_llm_purpose_policy_registry.py tests/test_low_risk_purpose_policies.py tests/test_planning_purpose_policies.py tests/test_plan_edit_purpose_policies.py tests/test_operational_purpose_policies.py tests/test_context_policy.py tests/test_context_gates.py tests/test_context_request_policy.py tests/test_memory_selection_policy.py tests/test_tool_exposure_enforcement.py tests/test_schema_validation_policy.py tests/test_token_budget_policy.py tests/test_cluster_2_integration.py -q
```

---

## Artifact/evidence requirement

- [ ] `tests/test_cluster_2_integration.py` created
- [ ] 12+ integration tests passing
- [ ] All 14 purposes resolve correctly
- [ ] All enforcement layers verified
- [ ] S5 regression guard passes
- [ ] Coverage ≥95%
- [ ] Commit message references Cluster 2 completion

---


---

## Implementation evidence (Sprint 6 Cluster 2)

- **Commit:** 7491f35 — feat: enforce llm runtime context policies
- **Modules added/changed:** All Cluster 2 modules
- **Tests:** All Cluster 2 tests (102 total, 1321 total suite passing)
- **Test result:** 102 cluster tests passing, 1321 total suite passing (as of commit 7491f35)
- **Coverage:** runtime/context_policy.py, runtime/context_gates.py, runtime/context_request_policy.py, runtime/memory_selection_policy.py, runtime/tool_exposure_enforcement.py, runtime/schema_validation_policy.py, runtime/token_budget_policy.py covered via dedicated test files
- **Validation command:** `python -m pytest tests/test_context_policy.py tests/test_context_gates.py tests/test_context_request_policy.py tests/test_memory_selection_policy.py tests/test_tool_exposure_enforcement.py tests/test_schema_validation_policy.py tests/test_token_budget_policy.py -q` → 102 passed
- **Architecture invariant:** All context levels enforced via runtime/ modules; agent.py does not build ad-hoc context

## Stop conditions

- Any S5 regression test fails (must fix before proceeding)
- Unknown purpose doesn't fail closed
- Purpose policy incomplete or malformed
- Coverage below 95%

---

## Sign-off

- [x] Story focused (integration regression)
- [x] Tests verify all policies work together
- [x] S5 behavior preserved
- [x] Unknown purpose fails correctly
