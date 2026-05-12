# S6-0103 Low-risk purpose policies

**Sprint:** Sprint 6  
**Cluster:** 1 (LLM Runtime Purpose Coverage)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0104, S6-0105, S6-0106, S6-0107  
**Blocked by:** S6-0102  

---

## Purpose

Complete policy metadata for 4 low-risk, no-tool LLM purposes: intent_classifier, clarification_generator, user_response_writer, trace_summarizer. No tools = no execution risk.

---

## Source rules

- Runtime Policy Spec: intent_classifier has no tools, outputs intent enum only
- Runtime Policy Spec: clarification_generator asks one focused question, maps to missing field
- Runtime Policy Spec: user_response_writer cannot claim execution success
- Runtime Policy Spec: trace_summarizer cannot mutate runtime truth
- Coverage requirement: 95% for new modules
- Modularization rule: policy logic in focused modules

---

## Current evidence

### What exists

- `runtime/llm_purpose_registry.py` — registry skeleton (from S6-0102)
- `runtime/prompt_packs.py` — persona/prompt packs exist
- `tests/test_llm_runtime_controller_contract.py` — controller tests

### What gaps exist

- No policy metadata for 4 low-risk purposes (will come in this story)
- No schema definitions for intent_classifier enum output
- No schema for clarification question format
- No validator for "cannot claim execution success" rule
- No test coverage for these 4 purposes

---

## Desired behavior

### High-level expectation

After S6-0103:

1. 4 low-risk purposes have complete policy metadata in registry
2. Each has schema (intent enum, question format, response text, summary text)
3. Each has validator (enum valid, question single, text-only no actions)
4. Each has fallback (ask_user or fail_closed)
5. Tests verify schema + validator for each

### Policy metadata shape

For each purpose:

```python
{
  "purpose_id": "intent_classifier",
  "model_class": "cheap",
  "context_policy": "user_message_only",
  "skill_policy": [],  # No skills
  "tool_policy": [],   # No tools
  "schema_id": "intent_enum_schema",
  "validator_id": "intent_validator",
  "fallback_policy": "ask_user",
  "telemetry_fields": ["purpose", "model", "intent_output", "tokens"]
}
```

### Purpose details

**intent_classifier**
- Input: user message
- Output: enum {click, fill, navigate, submit, assert, accept, custom, unknown}
- Validator: must be in enum set
- Fallback: ask_user "Which action intent?"

**clarification_generator**
- Input: user message + missing field name
- Output: single question string
- Validator: question string only, no actions
- Fallback: ask_user with default question

**user_response_writer**
- Input: execution result + user expectations
- Output: response text
- Validator: text-only, no "execution succeeded" claims unless caller confirms
- Fallback: generic response

**trace_summarizer**
- Input: execution trace
- Output: summary text
- Validator: text-only, cannot describe state changes
- Fallback: generic summary

---

## Out of scope

- Do not implement live calls for these purposes (wiring comes in Cluster 2+)
- Do not build frontend cards/UI
- Do not run paid LLM

---

## Allowed files

- `runtime/llm_purpose_policy.py` (modify: add 4 purpose policies)
- `runtime/llm_purpose_registry.py` (modify: add 4 purposes to registry)
- `runtime/intent_validator.py` (new, if modular validation desired)
- `runtime/clarification_validator.py` (new, if modular)
- `tests/test_low_risk_purpose_policies.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ frontend/
- ✗ Existing tests

---

## Tests first (required structure)

### Unit tests

- `test_intent_classifier_has_no_tools()`
- `test_intent_classifier_has_enum_schema()`
- `test_intent_classifier_validator_accepts_valid_intent()`
- `test_intent_classifier_validator_rejects_invalid_intent()`
- `test_clarification_generator_validator_accepts_question_string()`
- `test_clarification_generator_validator_rejects_action_claims()`
- `test_user_response_writer_validator_accepts_text()`
- `test_user_response_writer_validator_rejects_execution_success_claim()`
- `test_trace_summarizer_validator_accepts_text()`
- `test_trace_summarizer_validator_rejects_state_change_descriptions()`

### Contract tests

- `test_intent_classifier_policy_maps_to_registry()`
- `test_clarification_generator_policy_maps_to_registry()`
- `test_user_response_writer_policy_maps_to_registry()`
- `test_trace_summarizer_policy_maps_to_registry()`
- `test_schema_failure_retries_once_then_falls_back()`
- `test_telemetry_includes_purpose_model_tokens()`

File: `tests/test_low_risk_purpose_policies.py`

---

## Implementation notes

### Approach

1. For each of 4 purposes, create policy dict:
   ```python
   INTENT_CLASSIFIER_POLICY = {
     "purpose_id": "intent_classifier",
     "model_class": "cheap",
     "context_policy": "user_message_only",
     "skill_policy": [],
     "tool_policy": [],
     "schema_id": "intent_enum_schema",
     "validator_id": "intent_enum_validator",
     "fallback_policy": "ask_user",
     "telemetry_fields": ["purpose", "model", "intent_output", "tokens", "latency"]
   }
   ```

2. Define schema objects (simple enums/types):
   ```python
   INTENT_ENUM_SCHEMA = {
     "type": "string",
     "enum": ["click", "fill", "navigate", "submit", "assert", "accept", "custom", "unknown"]
   }
   ```

3. Define validators (functions that check output against schema):
   ```python
   def intent_enum_validator(output: Any) -> bool:
       return output in INTENT_ENUM_SCHEMA["enum"]
   ```

4. Add all 4 to PURPOSE_REGISTRY

5. Write tests for each validator (10+ tests total)

### Key invariants

- 4 purposes have zero tools (optimization + safety)
- Validators enforce strict schema (no prose)
- Fallback is explicit (not silent retry)
- Telemetry captures outcome

---

## Coverage requirement

```bash
python -m pytest tests/test_low_risk_purpose_policies.py --cov=runtime.llm_purpose_policy --cov=runtime.intent_validator --cov=runtime.clarification_validator --cov-fail-under=95
```

95% minimum for new validators.

---

## Validation commands

```bash
# Run low-risk purpose tests
python -m pytest tests/test_low_risk_purpose_policies.py -q

# Check all 4 purposes in registry
python -c "
from runtime.llm_purpose_registry import PURPOSE_REGISTRY
for p_id in ['intent_classifier', 'clarification_generator', 'user_response_writer', 'trace_summarizer']:
  p = PURPOSE_REGISTRY.get(p_id)
  print(f'{p_id}: tools={len(p.tool_policy)}, validator={p.validator_id}')
"

# Regression guard
python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_convergence_contract.py -q
```

---

## Artifact/evidence requirement

- [ ] 4 purpose policies added to registry
- [ ] Schema definitions for each purpose
- [ ] Validators for each purpose (4+ validators)
- [ ] Tests passing (10+ tests)
- [ ] Coverage ≥95%
- [ ] Regression guard passes
- [ ] Commit message references 4 low-risk purposes

---

## Stop conditions

- Cannot define schema for a purpose (clarify with spec)
- Existing tests fail after policy addition
- Coverage below 95%

---

## Sign-off

- [x] Story focused (4 low-risk purposes)
- [x] Tests designed (10+ unit/contract)
- [x] No tools exposed to unsafe purposes
- [x] Validators are strict
