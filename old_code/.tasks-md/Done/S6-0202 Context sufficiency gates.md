# S6-0202 Context sufficiency gates

**Sprint:** Sprint 6  
**Cluster:** 2 (Context/Memory/Token/Tool/Schema Policy Enforcement)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0203, S6-0204, S6-0207, S6-0208  
**Blocked by:** S6-0201  

---

## Purpose

Implement context sufficiency gates. Backend checks: user goal clear? page state known? required data available? If gate fails, request escalation instead of calling LLM with insufficient context.

---

## Source rules

- Runtime Policy Spec: sufficiency gates exist for major purpose families
- Runtime Policy Spec: gates fail → ask_user, not auto-escalate to L5
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/context_policy.py` (from S6-0201)
- `runtime/llm_purpose_policy.py` — 14 purposes with constraints

### What gaps exist

- No gate logic (will add in this story)
- No sufficiency checks before LLM calls
- No ASK_USER response path (from gates failing)

---

## Desired behavior

### Gate definitions per purpose family

**Intent classification**
- Gate: user goal is one sentence or less (clarity)
- Fail: ask "Could you rephrase your intention?"

**Page recommendations**
- Gate: page state known, page intelligence available
- Fail: ask "Can you describe the current page state?"

**Journey planning**
- Gate: required fields available (which pages, which data types)
- Fail: ask "Which pages must the journey visit?"

**Step planning**
- Gate: stable step IDs available, page state snapshot exists
- Fail: ask "What is the target element?"

**Locator specialist**
- Gate: validation result exists (what to find)
- Fail: ask "What element are you trying to find?"

**Recovery**
- Gate: failed operation evidence available
- Fail: ask "What went wrong?"

---

## Out of scope

- Do not implement context escalation logic (that's S6-0203)
- Do not implement Page Intelligence live
- Do not run paid LLM

---

## Allowed files

- `runtime/context_gates.py` (new)
- `tests/test_context_gates.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ Context request handler (S6-0203)

---

## Tests first

### Unit tests

- `test_intent_gate_passes_if_goal_clear()`
- `test_intent_gate_fails_if_ambiguous()`
- `test_page_recommendation_gate_requires_page_state()`
- `test_journey_planning_gate_requires_pages_list()`
- `test_step_planning_gate_requires_step_ids()`
- `test_locator_gate_requires_validation_result()`
- `test_recovery_gate_requires_failure_evidence()`
- `test_failed_gate_returns_clarification_request()`

### Contract tests

- `test_controller_checks_gate_before_llm_call()`
- `test_failed_gate_emits_ask_user()`

File: `tests/test_context_gates.py`

---

## Implementation notes

### Approach

1. Create `context_gates.py`:
   ```python
   SUFFICIENCY_GATES = {
     "intent_classifier": [
       ("goal_clarity", lambda ctx: len(ctx.user_goal.split(".")) == 1),
       ...
     ],
     "page_validation_recommender": [
       ("page_state_known", lambda ctx: ctx.page_state is not None),
       ("page_intelligence_available", lambda ctx: ctx.page_intelligence is not None),
     ],
     ...
   }
   
   def check_gates(purpose_id: str, context: Context) -> Gate.Result:
       gates = SUFFICIENCY_GATES.get(purpose_id, [])
       for gate_name, gate_fn in gates:
           if not gate_fn(context):
               return Gate.Result(passed=False, failed_gate=gate_name)
       return Gate.Result(passed=True)
   ```

2. Define clarification questions per gate:
   ```python
   GATE_CLARIFICATIONS = {
     "goal_clarity": "Could you rephrase your intention?",
     ...
   }
   ```

3. Add gate checking to controller flow (minimal, test-backed)

4. Write tests (8+ unit, 2+ contract)

### Key invariants

- Gates prevent bad LLM calls (fail fast)
- Failed gate → ask_user, never silent escalation
- Gates are purpose-specific

---

## Coverage requirement

95% for context_gates.py.

---

## Validation commands

```bash
python -m pytest tests/test_context_gates.py -q
python -c "from runtime.context_gates import SUFFICIENCY_GATES; print(f'Loaded gates for {len(SUFFICIENCY_GATES)} purposes')"
```

---

## Artifact/evidence requirement

- [ ] `runtime/context_gates.py` — sufficiency gates for 6+ purpose families
- [ ] Gate clarifications defined
- [ ] 10+ tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references context gates

---


---

## Implementation evidence (Sprint 6 Cluster 2)

- **Commit:** 7491f35 — feat: enforce llm runtime context policies
- **Modules added/changed:** runtime/context_gates.py
- **Tests:** tests/test_context_gates.py
- **Test result:** 102 cluster tests passing, 1321 total suite passing (as of commit 7491f35)
- **Coverage:** runtime/context_policy.py, runtime/context_gates.py, runtime/context_request_policy.py, runtime/memory_selection_policy.py, runtime/tool_exposure_enforcement.py, runtime/schema_validation_policy.py, runtime/token_budget_policy.py covered via dedicated test files
- **Validation command:** `python -m pytest tests/test_context_policy.py tests/test_context_gates.py tests/test_context_request_policy.py tests/test_memory_selection_policy.py tests/test_tool_exposure_enforcement.py tests/test_schema_validation_policy.py tests/test_token_budget_policy.py -q` → 102 passed
- **Architecture invariant:** All context levels enforced via runtime/ modules; agent.py does not build ad-hoc context

## Stop conditions

- Cannot define clear gate for a purpose (clarify with spec)
- Coverage below 95%

---

## Sign-off

- [x] Story focused (sufficiency gates)
- [x] Tests verify gates block bad calls
- [x] Clarifications clear
