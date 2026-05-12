# BUG-S6-FINAL-001: Pre-existing model-class contract mismatch failures

**Status:** Backlog  
**Severity:** Medium — blocks cheap regression cleanliness; does not block local fixture E2E or runtime behavior  
**Owner:** Cluster 2 / model routing policy follow-up  
**Sprint:** Sprint 6 Cluster 12 gap  
**Filed:** 2026-05-13  

---

## Title

Pre-existing model-class contract mismatch: tests assert `"cheap"` / `"main"` but runtime returns provider model name (`"gpt-4o-mini"`)

---

## Observed failures (12 total)

### Affected files

- `tests/test_llm_planning_contracts.py` — 4 failures
- `tests/test_llm_specialist_contracts.py` — 6 failures
- `tests/test_llm_policy_gateway.py` — 2 failures

### Failure example

```
FAILED tests/test_llm_planning_contracts.py::test_llm_005_intent_classifier_returns_clarification_ready_payload
AssertionError: assert 'gpt-4o-mini' == 'cheap'
  - cheap
  + gpt-4o-mini
```

### Full list of failing tests

1. `test_llm_planning_contracts.py::test_llm_005_intent_classifier_returns_clarification_ready_payload`
2. `test_llm_planning_contracts.py::test_llm_005_clarification_generator_returns_user_followup_payload`
3. `test_llm_planning_contracts.py::test_llm_006_journey_planner_returns_structured_plan_proposal`
4. `test_llm_planning_contracts.py::test_llm_007_plan_diff_editor_returns_mutation_only_diff`
5. `test_llm_specialist_contracts.py::test_llm_008_locator_specialist_advisory_only_boundary`
6. `test_llm_specialist_contracts.py::test_llm_009_recovery_diagnoser_contract_and_runtime_truth_boundary`
7. `test_llm_specialist_contracts.py::test_llm_010_deterministic_trace_summarizer_skips_model_call_and_keeps_budget_metadata`
8. `test_llm_specialist_contracts.py::test_llm_010_budget_guard_rejects_over_budget_calls_without_model_call`
9. `test_llm_specialist_contracts.py::test_llm_008_009_invalid_specialist_outputs_fail_closed[locator_specialist-validator0-response0-5]`
10. `test_llm_specialist_contracts.py::test_llm_008_009_invalid_specialist_outputs_fail_closed[recovery_diagnoser-validator1-response1-2]`
11. `test_llm_policy_gateway.py::test_gateway_returns_purpose_specific_decision_for_planning`
12. `test_llm_policy_gateway.py::test_gateway_restricts_tools_by_purpose`

---

## Root cause

The `model_router.py` resolves model_class (`cheap`, `main`) to a concrete provider model name (e.g. `gpt-4o-mini`).
The runtime returns the resolved provider model name in the result payload field `model`.
However, the contract tests assert the abstract model_class string (`"cheap"`) not the provider string.

This is a test/contract alignment issue — the implementation is consistent internally, but the tests use the wrong expected value.

---

## Classification

- These failures **pre-existed before Sprint 6 Cluster 1** autonomous implementation.
- They are **cheap-suite blockers** — they fail without any paid/live LLM call.
- They are **NOT hidden** — they appear in every full regression run.
- The runtime behavior is not broken; the tests assert the wrong abstraction layer.

---

## Expected fix

Two acceptable resolutions:

**Option A (preferred):** Update contract tests to assert `result["model_class"] == "cheap"` (use the policy key, not the resolved provider name) if `model_class` is separately exposed in the result.

**Option B:** Update contract tests to assert the resolved provider model name (e.g. `"gpt-4o-mini"`) and add a model_class/provider mapping check.

Do NOT use `xfail` or skip to hide these failures.

---

## Impact

- `python -m pytest -q` shows 12 failures in every run until fixed.
- Full regression is otherwise clean (1689 passed, 1 skipped).
- These failures do not block architecture invariants, local fixture E2E, or runtime module correctness.
- They DO block claiming a fully-green cheap regression suite.

---

## Recommended priority

Fix before claiming Sprint 6 cheap regression gate is fully green.
Do not merge/push claiming clean regression without addressing or explicitly excluding these with documented rationale.
