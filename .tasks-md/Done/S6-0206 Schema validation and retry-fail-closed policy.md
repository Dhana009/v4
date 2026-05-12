# S6-0206 Schema validation and retry/fail-closed policy

**Sprint:** Sprint 6  
**Cluster:** 2 (Context/Memory/Token/Tool/Schema Policy Enforcement)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0207, S6-0208  
**Blocked by:** S6-0205  

---

## Purpose

Enforce schema validation + retry/fail-closed behavior. Invalid schema triggers one retry; second failure fails closed or asks user. Prose output never becomes runtime truth.

---

## Source rules

- Runtime Policy Spec: every purpose has schema
- Runtime Policy Spec: schema failure retries once, then fails closed
- Runtime Policy Spec: prose cannot silently continue
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/llm_purpose_policy.py` — every purpose has schema_id (from Cluster 1)
- `runtime/llm_purpose_policy.py` — every purpose has validator_id (from Cluster 1)
- Validator examples: intent_enum_validator, planning_schema_validator, etc.

### What gaps exist

- No runtime validation enforcement (policies defined but not enforced)
- No retry logic on schema failure
- No fail-closed fallback

---

## Desired behavior

### Schema validation flow

```
1. LLM returns output
2. Controller calls validator(output)
3. If valid → use output
4. If invalid → log "schema_error", try ONE retry
5. If retry valid → use output
6. If retry invalid → log "schema_failure", apply fallback
   - Fallback: ask_user, fail_closed, or escalate (per purpose)
7. Never silently accept prose (always validate)
```

### Fallback per purpose

```
intent_classifier           → ask_user "Could you clarify intent?"
step_plan_normalizer        → ask_user "Could you rephrase?"
recovery_diagnoser          → fail_closed (return no_recovery_path)
execution_driver            → skip operation
...
```

---

## Out of scope

- Do not implement schema definitions (exist from Cluster 1)
- Do not change validator implementations
- Do not run paid LLM

---

## Allowed files

- `runtime/schema_validation_policy.py` (new)
- `tests/test_schema_validation_policy.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ Validator implementations (already exist)

---

## Tests first

### Unit tests

- `test_valid_schema_passes()`
- `test_invalid_schema_triggers_one_retry()`
- `test_second_schema_invalid_applies_fallback()`
- `test_prose_output_without_schema_is_invalid()`
- `test_content_only_response_fails_schema()`
- `test_fallback_logged_with_purpose_and_error()`
- `test_retry_count_logged()`

### Contract tests

- `test_controller_validates_schema_before_using_output()`
- `test_planning_purpose_invalid_schema_asks_user()`
- `test_recovery_purpose_invalid_schema_fails_closed()`

File: `tests/test_schema_validation_policy.py`

---

## Implementation notes

### Approach

1. Create `schema_validation_policy.py`:
   ```python
   def validate_and_retry(purpose_id: str, llm_output: str, max_retries=1):
       policy = PURPOSE_REGISTRY.get(purpose_id)
       validator_id = policy.validator_id
       validator_fn = VALIDATOR_REGISTRY[validator_id]
       
       if validator_fn(llm_output):
           return {"valid": True, "output": llm_output}
       
       # Invalid: retry once
       if max_retries > 0:
           # Call LLM again with "please follow schema" hint
           retry_output = call_llm_with_schema_hint(...)
           if validator_fn(retry_output):
               return {"valid": True, "output": retry_output, "retried": True}
       
       # Both attempts failed: apply fallback
       fallback = policy.fallback_policy
       return {"valid": False, "fallback": fallback, "reason": "schema_failure"}
   ```

2. Add logging:
   - Log schema failures with purpose/validator/error
   - Log retries
   - Log fallback decision

3. Integrate with controller (minimal)

4. Write tests (7+ unit, 2+ contract)

### Key invariants

- Invalid schema always retried once (never silent failure)
- Prose output never accepted (always validated)
- Fallback is explicit (logged, not hidden)
- Retry includes schema hint in second prompt

---

## Coverage requirement

95% for schema_validation_policy.py.

---

## Validation commands

```bash
python -m pytest tests/test_schema_validation_policy.py -q
python -c "
from runtime.llm_purpose_policy import PURPOSE_REGISTRY
for p_id in ['intent_classifier', 'step_plan_normalizer', 'recovery_diagnoser']:
  policy = PURPOSE_REGISTRY.get(p_id)
  print(f'{p_id}: validator={policy.validator_id}, fallback={policy.fallback_policy}')
"
```

---

## Artifact/evidence requirement

- [ ] `runtime/schema_validation_policy.py` — validation + retry logic
- [ ] Retry with schema hint mechanism
- [ ] Fallback handling per purpose
- [ ] 9+ tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references schema validation

---


---

## Implementation evidence (Sprint 6 Cluster 2)

- **Commit:** 7491f35 — feat: enforce llm runtime context policies
- **Modules added/changed:** runtime/schema_validation_policy.py
- **Tests:** tests/test_schema_validation_policy.py
- **Test result:** 102 cluster tests passing, 1321 total suite passing (as of commit 7491f35)
- **Coverage:** runtime/context_policy.py, runtime/context_gates.py, runtime/context_request_policy.py, runtime/memory_selection_policy.py, runtime/tool_exposure_enforcement.py, runtime/schema_validation_policy.py, runtime/token_budget_policy.py covered via dedicated test files
- **Validation command:** `python -m pytest tests/test_context_policy.py tests/test_context_gates.py tests/test_context_request_policy.py tests/test_memory_selection_policy.py tests/test_tool_exposure_enforcement.py tests/test_schema_validation_policy.py tests/test_token_budget_policy.py -q` → 102 passed
- **Architecture invariant:** All context levels enforced via runtime/ modules; agent.py does not build ad-hoc context

## Stop conditions

- Validator functions missing (verify registry)
- Cannot define schema hint for retry
- Coverage below 95%

---

## Sign-off

- [x] Story focused (schema validation + retry)
- [x] Tests verify retry behavior
- [x] Prose rejection enforced
- [x] Fallback explicit
