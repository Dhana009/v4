# S6-0204 Memory selection policy

**Sprint:** Sprint 6  
**Cluster:** 2 (Context/Memory/Token/Tool/Schema Policy Enforcement)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0207, S6-0208  
**Blocked by:** S6-0203  

---

## Purpose

Implement memory selection policy. Backend stores detailed memory but LLM receives only relevant selected subset. Old plans/traces not sent by default unless purpose needs them.

---

## Source rules

- Runtime Policy Spec: full chat history not sent by default
- Runtime Policy Spec: old plans/traces stored but not auto-included
- Runtime Policy Spec: memory selection logged with reason
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/context_policy.py` (from S6-0201)
- Recording/persistence framework exists but memory selection not implemented

### What gaps exist

- No memory selection logic
- No filtering of old plans from LLM context
- No memory retrieval API

---

## Desired behavior

### Memory selection rules

By default, LLM receives:
- Current user message
- Current page state
- Current plan (if in planning/correction phase)
- Current error/recovery context (if in recovery)

By request, LLM can access:
- Previous accepted plans (if comparing to similar plan)
- Previous rejected plans (if learning from mistakes)
- Previous locator decisions (if same target element)
- Execution traces (if debugging similar step)

### Selection per purpose

```
intent_classifier        → current message only
clarification_generator  → current message + field name
page_validation_recommender → current page + intelligence
journey_planner          → current page + requirements
step_plan_normalizer     → current plan + page + locator context
recovery_diagnoser       → current error + recent trace (last 3 steps)
replay_repair_specialist → original trace + replay failure
custom_assertion_planner → current result + original step
...
```

---

## Out of scope

- Do not implement full memory persistence (assumed to exist)
- Do not build memory search/retrieval UI
- Do not run paid LLM

---

## Allowed files

- `runtime/memory_selection_policy.py` (new)
- `tests/test_memory_selection_policy.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ Persistence layer changes

---

## Tests first

### Unit tests

- `test_full_chat_history_not_sent_by_default()`
- `test_old_plans_excluded_unless_relevant()`
- `test_execution_traces_excluded_unless_debugging()`
- `test_memory_selection_per_purpose_correct()`
- `test_memory_selection_logged_with_reason()`
- `test_secrets_excluded_from_memory()`
- `test_maximum_memory_size_enforced()`

### Contract tests

- `test_controller_uses_memory_selection_policy()`
- `test_step_planning_includes_only_current_plan()`

File: `tests/test_memory_selection_policy.py`

---

## Implementation notes

### Approach

1. Create `memory_selection_policy.py`:
   ```python
   MEMORY_SELECTION_DEFAULTS = {
     "intent_classifier": ["user_message"],
     "page_validation_recommender": ["user_message", "page_state", "page_intelligence"],
     "step_plan_normalizer": ["user_message", "current_plan", "page_state"],
     "recovery_diagnoser": ["error_context", "recent_trace"],
     ...
   }
   
   def select_memory_for_purpose(purpose_id, all_memory, max_size=20000):
       categories = MEMORY_SELECTION_DEFAULTS[purpose_id]
       selected = [m for m in all_memory if m.category in categories]
       return truncate_to_size(selected, max_size)
   ```

2. Add memory filters:
   - Exclude full history by default
   - Exclude old plans unless explicitly relevant
   - Exclude secrets/credentials

3. Add selection logging (what was selected, why, tokens)

4. Write tests (7+ unit, 2+ contract)

### Key invariants

- Memory selection is purpose-specific
- Old plans/traces stored but not auto-sent
- Full history never sent (prevents prompt inflation)
- Selection logged for debugging

---

## Coverage requirement

95% for memory_selection_policy.py.

---

## Validation commands

```bash
python -m pytest tests/test_memory_selection_policy.py -q
python -c "from runtime.memory_selection_policy import MEMORY_SELECTION_DEFAULTS; print(f'Loaded {len(MEMORY_SELECTION_DEFAULTS)} purposes')"
```

---

## Artifact/evidence requirement

- [ ] `runtime/memory_selection_policy.py` — selection rules per purpose
- [ ] Memory filters (history, secrets, size)
- [ ] 9+ tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references memory selection

---


---

## Implementation evidence (Sprint 6 Cluster 2)

- **Commit:** 7491f35 — feat: enforce llm runtime context policies
- **Modules added/changed:** runtime/memory_selection_policy.py
- **Tests:** tests/test_memory_selection_policy.py
- **Test result:** 102 cluster tests passing, 1321 total suite passing (as of commit 7491f35)
- **Coverage:** runtime/context_policy.py, runtime/context_gates.py, runtime/context_request_policy.py, runtime/memory_selection_policy.py, runtime/tool_exposure_enforcement.py, runtime/schema_validation_policy.py, runtime/token_budget_policy.py covered via dedicated test files
- **Validation command:** `python -m pytest tests/test_context_policy.py tests/test_context_gates.py tests/test_context_request_policy.py tests/test_memory_selection_policy.py tests/test_tool_exposure_enforcement.py tests/test_schema_validation_policy.py tests/test_token_budget_policy.py -q` → 102 passed
- **Architecture invariant:** All context levels enforced via runtime/ modules; agent.py does not build ad-hoc context

## Stop conditions

- Cannot define what makes old plan "relevant" (clarify spec)
- Coverage below 95%

---

## Sign-off

- [x] Story focused (memory selection)
- [x] Tests verify old history excluded
- [x] Size limits enforced
