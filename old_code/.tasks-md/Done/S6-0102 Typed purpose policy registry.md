# S6-0102 Typed purpose policy registry

**Sprint:** Sprint 6  
**Cluster:** 1 (LLM Runtime Purpose Coverage)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0103, S6-0104, S6-0105, S6-0106, S6-0107, S6-0201, S6-0202, S6-0203, S6-0204  
**Blocked by:** S6-0101  

---

## Purpose

Create single typed policy registry containing all 14 LLM purposes with complete metadata. Registry is source of truth: every purpose has model/context/skill/tool/schema/validator/fallback policy. Unknown purpose fails closed.

---

## Source rules

- Runtime Policy Spec: every LLM call must declare purpose
- Runtime Policy Spec: unknown purpose must fail closed (no fallback LLM call)
- Coverage requirement: 95% for new runtime policy modules
- Modularization rule: policy logic goes in focused runtime/ modules, not agent.py

---

## Current evidence

### What exists in the repo

- `runtime/llm_runtime_controller.py` — controller exists but doesn't enforce purpose registry
- `runtime/model_router.py` — routes cheap/main/debug but not purpose-specific
- `runtime/skill_policy.py` — loads skills, not purpose-indexed
- `runtime/tool_schema_policy.py` — filters tools, not purpose-indexed
- 14 required purposes listed in Runtime Policy Spec

### What gaps exist

- No unified purpose registry (policies scattered across files)
- No dataclass/TypedDict for purpose metadata
- No registry lookup (purpose_id → policy object)
- No unknown-purpose handling (unknown purpose should fail closed, not skip to fallback)
- Controller doesn't validate purpose parameter

---

## Desired behavior

### High-level expectation

After S6-0102:

1. Single registry object with all 14 purposes
2. Each purpose has type-safe metadata
3. Registry lookup is O(1)
4. Unknown purpose lookup raises/fails with clear error
5. Controller can look up purpose and enforce policy

### Interface changes

Before:

```python
# Controller doesn't enforce purpose
controller.call_llm(
  messages=[...],
  model="gpt-4o-mini"
)
```

After:

```python
# Controller looks up purpose and enforces policy
purpose_policy = purpose_registry.get(purpose_id="step_plan_normalizer")
controller.call_llm(
  purpose_id="step_plan_normalizer",
  messages=[...],
  # context/tools/schema/validator/fallback come from purpose_policy
)

# Unknown purpose fails:
purpose_policy = purpose_registry.get(purpose_id="unknown_purpose")  # Raises ValueError
```

### New files required

- `runtime/llm_purpose_policy.py` — TypedDict/dataclass for purpose metadata
- `runtime/llm_purpose_registry.py` — registry with all 14 purposes
- `tests/test_llm_purpose_policy_registry.py` — registry tests

### Modified files

- `runtime/llm_runtime_controller.py` — calls registry.get() to enforce policy (minimal)

---

## Out of scope

- Do not implement live LLM calls from new registry (that's Clusters 1–2 later)
- Do not wire registry into agent.py yet (orchestration changes come later)
- Do not add frontend/browser behavior
- Do not run paid LLM

---

## Allowed files

- `runtime/llm_purpose_policy.py` (new)
- `runtime/llm_purpose_registry.py` (new)
- `tests/test_llm_purpose_policy_registry.py` (new)
- `runtime/llm_runtime_controller.py` (modify: add registry.get() call, minimal)

---

## Forbidden files

- ✗ agent.py (no orchestration changes yet)
- ✗ server.py
- ✗ frontend/ (no browser changes)
- ✗ Existing tests (except minimal controller changes)

---

## Tests first (required structure)

### Unit tests

- `test_purpose_registry_has_all_14_purposes()` — all 14 required purposes exist
- `test_purpose_registry_unknown_purpose_raises_value_error()` — unknown purpose fails closed
- `test_purpose_policy_has_required_fields()` — every purpose has model_class, context_policy, skill_policy, tool_policy, schema_id, validator_id, fallback_policy
- `test_purpose_model_class_is_valid()` — model class is cheap/main/debug or literal model name
- `test_purpose_context_policy_is_valid()` — context level is L0–L5 or valid policy reference
- `test_purpose_skill_policy_is_list()` — skills are list of valid skill IDs
- `test_purpose_tool_policy_is_list()` — tools are list of valid tool IDs
- `test_purpose_schema_id_exists()` — schema_id points to valid schema
- `test_purpose_validator_id_exists_or_none()` — validator_id is valid or None
- `test_purpose_fallback_policy_is_valid()` — fallback is "ask_user"/"fail_closed"/"retry" etc.

### Contract tests

- `test_controller_calls_registry_for_purpose_metadata()` — controller.call_llm() looks up purpose
- `test_controller_unknown_purpose_fails_immediately()` — unknown purpose raises before LLM call
- `test_controller_propagates_purpose_policy_to_llm_call()` — purpose policy metadata is passed through

### Regression tests

None yet (added to regression guard in later story).

File: `tests/test_llm_purpose_policy_registry.py`

---

## Implementation notes

### Approach

1. Define `LLMPurposePolicy` TypedDict or dataclass with fields:
   - purpose_id: str
   - model_class: str (cheap/main/debug)
   - context_policy: str (reference or inline)
   - skill_policy: List[str] (skill IDs allowed)
   - tool_policy: List[str] (tool IDs allowed)
   - schema_id: str (output schema)
   - validator_id: Optional[str] (validator function)
   - fallback_policy: str (ask_user/fail_closed/retry)
   - telemetry_fields: Dict[str, Any]

2. Create `LLMPurposeRegistry`:
   - Import all 14 purpose policies
   - Store as dict: purpose_id → policy
   - Method: `get(purpose_id: str) → LLMPurposePolicy` (raises ValueError if not found)

3. Populate registry with all 14 purposes:
   - intent_classifier
   - clarification_generator
   - page_intelligence_summarizer
   - page_validation_recommender
   - journey_planner
   - step_plan_normalizer
   - plan_diff_editor
   - locator_specialist
   - custom_assertion_planner
   - execution_driver
   - recovery_diagnoser
   - replay_repair_specialist
   - user_response_writer
   - trace_summarizer

4. Modify `llm_runtime_controller.py`:
   - On controller initialization, import registry
   - On `call_llm(purpose_id=...)`, call `registry.get(purpose_id)` first
   - Pass policy metadata to LLM call site

5. Write tests covering all 14 purposes and failure cases

### Key invariants

- Registry is immutable (policies don't change at runtime)
- Unknown purpose raises ValueError (fail-closed)
- Every purpose has all required fields (type-safe)
- Controller cannot bypass registry lookup

---

## Coverage requirement

```bash
python -m pytest tests/test_llm_purpose_policy_registry.py --cov=runtime.llm_purpose_policy --cov=runtime.llm_purpose_registry --cov-fail-under=95
```

Minimum 95% for new modules. Branch coverage for unknown-purpose error path.

---

## Validation commands

```bash
# Run purpose registry tests
python -m pytest tests/test_llm_purpose_policy_registry.py -q

# Check coverage
python -m pytest tests/test_llm_purpose_policy_registry.py --cov=runtime.llm_purpose_policy --cov=runtime.llm_purpose_registry --cov-fail-under=95 -q

# Verify registry import works
python -c "from runtime.llm_purpose_registry import PURPOSE_REGISTRY; print(f'Loaded {len(PURPOSE_REGISTRY.purposes)} purposes')"

# Run regression guard
python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_convergence_contract.py -q
```

---

## Artifact/evidence requirement

- [ ] `runtime/llm_purpose_policy.py` — TypedDict/dataclass for purpose metadata
- [ ] `runtime/llm_purpose_registry.py` — registry with all 14 purposes
- [ ] `tests/test_llm_purpose_policy_registry.py` — unit/contract tests (10+ tests)
- [ ] `runtime/llm_runtime_controller.py` — minimal change (add registry.get() call)
- [ ] Coverage ≥95%
- [ ] Regression guard passes
- [ ] Commit message references Cluster 1 purpose coverage goal

---

## Stop conditions

- Cannot determine which of 14 purposes should be in registry (check Runtime Policy Spec)
- Existing controller tests fail after registry addition (must fix before proceeding)
- Coverage below 95% (investigate root cause before lowering requirement)

---

## Sign-off

- [x] Story is specific (build typed registry)
- [x] Tests are designed (10+ unit/contract)
- [x] Modularization followed (new modules in runtime/)
- [x] No forbidden files touched
- [x] Coverage requirement clear (95%)
- [x] Stop conditions listed
