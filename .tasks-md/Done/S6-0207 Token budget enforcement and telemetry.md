# S6-0207 Token budget enforcement and telemetry

**Sprint:** Sprint 6  
**Cluster:** 2 (Context/Memory/Token/Tool/Schema Policy Enforcement)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0208  
**Blocked by:** S6-0206  

---

## Purpose

Enforce token budgets per purpose. Log all LLM calls with purpose/model/context_level/tokens/latency. Budget exceeded triggers compaction or clarification, never silent truncation.

---

## Source rules

- Runtime Policy Spec: token budget enforced per purpose
- Runtime Policy Spec: budget exceeded → compact context or ask_user, not silent truncation
- Runtime Policy Spec: all calls logged with purpose/model/tokens
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/telemetry.py` (Sprint 5)
- Token counting infrastructure exists

### What gaps exist

- No per-purpose token budget enforcement
- No budget exceeded handling
- Logging is partial (not all calls tracked)

---

## Desired behavior

### Token budgets per purpose (examples)

```
intent_classifier           → 500 input max
clarification_generator     → 500 input max
page_validation_recommender → 1500 input max
journey_planner             → 2000 input max
step_plan_normalizer        → 2000 input max
recovery_diagnoser          → 1500 input max (no L5 by default)
execution_driver            → 500 input max
...
```

### Budget exceeded handling

```
1. If context can be compacted (e.g., remove old traces) → compact + retry
2. Else if purpose allows escalation → ask_user for clarification
3. Else → fail_closed (no LLM call)
```

### Telemetry per call

```
{
  "purpose": "step_plan_normalizer",
  "model": "gpt-4o-mini",
  "context_level": "L1",
  "context_tokens": 1200,
  "skills_tokens": 300,
  "tools_tokens": 200,
  "total_input_tokens": 1700,
  "output_tokens": 45,
  "latency_ms": 2340,
  "finish_reason": "stop",
  "schema_validation": "passed",
  "result": "success"
}
```

---

## Out of scope

- Do not implement token counting (assume it exists)
- Do not change model routing
- Do not run paid LLM

---

## Allowed files

- `runtime/token_budget_policy.py` (new)
- `tests/test_token_budget_policy.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ Telemetry module (existing)

---

## Tests first

### Unit tests

- `test_each_purpose_has_token_budget()`
- `test_budget_exceeded_triggers_compaction_or_clarification()`
- `test_compaction_reduces_context_tokens()`
- `test_clarification_asked_if_compaction_insufficient()`
- `test_fail_closed_if_no_escalation_allowed()`
- `test_telemetry_includes_purpose_model_tokens()`
- `test_telemetry_includes_latency()`
- `test_budget_exceeded_logged()`

### Contract tests

- `test_controller_checks_token_budget_before_call()`
- `test_single_call_budget_enforced()`

File: `tests/test_token_budget_policy.py`

---

## Implementation notes

### Approach

1. Create `token_budget_policy.py`:
   ```python
   PURPOSE_TOKEN_BUDGETS = {
     "intent_classifier": 500,
     "step_plan_normalizer": 2000,
     ...
   }
   
   def check_and_enforce_budget(purpose_id: str, context_tokens: int) -> Result:
       budget = PURPOSE_TOKEN_BUDGETS[purpose_id]
       if context_tokens > budget:
           # Try to compact
           compacted = compact_context(context_tokens, budget)
           if compacted:
               return {"enforced": True, "action": "compact"}
           else:
               # Cannot compact enough, ask user
               return {"enforced": True, "action": "ask_clarification"}
       return {"enforced": True, "action": "proceed"}
   ```

2. Add telemetry collection:
   - Capture all LLM calls with metadata
   - Log before and after validation
   - Include timing

3. Integrate with controller (minimal)

4. Write tests (8+ unit, 2+ contract)

### Key invariants

- Budget never silently exceeded (always action taken)
- Compaction preferred over ask_user
- All calls logged for observability
- Budget override not allowed (no way to bypass)

---

## Coverage requirement

95% for token_budget_policy.py.

---

## Validation commands

```bash
python -m pytest tests/test_token_budget_policy.py -q
python -c "
from runtime.token_budget_policy import PURPOSE_TOKEN_BUDGETS
print(f'Loaded {len(PURPOSE_TOKEN_BUDGETS)} purpose budgets')
for p in list(PURPOSE_TOKEN_BUDGETS.keys())[:3]:
  print(f'{p}: {PURPOSE_TOKEN_BUDGETS[p]} tokens')
"
```

---

## Artifact/evidence requirement

- [ ] `runtime/token_budget_policy.py` — budgets per purpose
- [ ] Budget enforcement logic (compact/escalate/fail)
- [ ] Telemetry collection + logging
- [ ] 10+ tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references token budgets

---


---

## Implementation evidence (Sprint 6 Cluster 2)

- **Commit:** 7491f35 — feat: enforce llm runtime context policies
- **Modules added/changed:** runtime/token_budget_policy.py
- **Tests:** tests/test_token_budget_policy.py
- **Test result:** 102 cluster tests passing, 1321 total suite passing (as of commit 7491f35)
- **Coverage:** runtime/context_policy.py, runtime/context_gates.py, runtime/context_request_policy.py, runtime/memory_selection_policy.py, runtime/tool_exposure_enforcement.py, runtime/schema_validation_policy.py, runtime/token_budget_policy.py covered via dedicated test files
- **Validation command:** `python -m pytest tests/test_context_policy.py tests/test_context_gates.py tests/test_context_request_policy.py tests/test_memory_selection_policy.py tests/test_tool_exposure_enforcement.py tests/test_schema_validation_policy.py tests/test_token_budget_policy.py -q` → 102 passed
- **Architecture invariant:** All context levels enforced via runtime/ modules; agent.py does not build ad-hoc context

## Stop conditions

- Cannot define token budgets per purpose (clarify with spec)
- Compaction logic undefined
- Coverage below 95%

---

## Sign-off

- [x] Story focused (token budgets + telemetry)
- [x] Tests verify budget enforcement
- [x] All calls logged
- [x] No silent truncation
