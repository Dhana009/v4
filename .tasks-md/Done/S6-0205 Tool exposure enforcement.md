# S6-0205 Tool exposure enforcement

**Sprint:** Sprint 6  
**Cluster:** 2 (Context/Memory/Token/Tool/Schema Policy Enforcement)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0206, S6-0207, S6-0208  
**Blocked by:** S6-0204  

---

## Purpose

Convert purpose tool policy from S6-0105/0106 into actual runtime enforcement. Controller builds tool schema per purpose; LLM cannot access tools not in purpose policy.

---

## Source rules

- Runtime Policy Spec: tool exposure enforced at runtime per purpose
- Cluster 1 (S6-0103–0106): tool policies defined per purpose
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/llm_purpose_policy.py` — 14 purposes with tool_policy field (from Cluster 1)
- `runtime/tool_schema_policy.py` — tool filtering logic (Sprint 5, partial)
- Tools defined: ask_user, needs_more_context, next_operation, locator_tools, inspection_tools, etc.

### What gaps exist

- tool_policy field in purpose not yet used (just defined)
- Controller doesn't filter tools by purpose
- No enforcement that unknown tools raise error

---

## Desired behavior

### Tool exposure matrix

For example:

```
intent_classifier           → [ask_user]
page_validation_recommender → [ask_user, needs_more_context]
page_intelligence_summarizer → []
step_plan_normalizer        → [ask_user, needs_more_context] + convergence constraint
locator_specialist          → [locator_tools, ask_user]
execution_driver            → [next_operation]
recovery_diagnoser          → [diagnostic_tools, ask_user]
...
```

### Enforcement

```python
def get_tools_for_purpose(purpose_id):
    policy = PURPOSE_REGISTRY.get(purpose_id)
    return build_tool_schemas(policy.tool_policy)

# Controller passes only allowed tools to LLM
tools = get_tools_for_purpose(purpose_id)
response = llm.call(messages=..., tools=tools)
```

---

## Out of scope

- Do not add new tools (tool definitions exist)
- Do not change convergence narrowing
- Do not run paid LLM

---

## Allowed files

- `runtime/tool_exposure_enforcement.py` (new)
- `tests/test_tool_exposure_enforcement.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ Tool definitions (already exist)
- ✗ Convergence narrowing

---

## Tests first

### Unit tests

- `test_intent_classifier_exposes_only_ask_user()`
- `test_page_validation_recommender_forbids_execution_tools()`
- `test_locator_specialist_forbids_action_tools()`
- `test_execution_driver_forbids_planning_tools()`
- `test_recovery_diagnoser_forbids_execution_tools()`
- `test_unknown_purpose_zero_tools()`
- `test_tool_exposure_per_purpose_matches_policy()`

### Contract tests

- `test_controller_enforces_tool_exposure_per_purpose()`
- `test_planning_purposes_forbid_browser_tools()`

File: `tests/test_tool_exposure_enforcement.py`

---

## Implementation notes

### Approach

1. Create `tool_exposure_enforcement.py`:
   ```python
   def get_allowed_tools(purpose_id: str) -> List[str]:
       policy = PURPOSE_REGISTRY.get(purpose_id)
       return policy.tool_policy
   
   def build_tool_schemas_for_purpose(purpose_id: str):
       allowed = get_allowed_tools(purpose_id)
       all_tools = TOOL_DEFINITIONS  # Existing tool registry
       return [all_tools[t] for t in allowed if t in all_tools]
   ```

2. Add validation:
   - Check that every tool in tool_policy exists
   - Fail if unknown tool referenced

3. Update controller to call `build_tool_schemas_for_purpose()` instead of global tools

4. Write tests (7+ unit, 2+ contract)

### Key invariants

- Only authorized tools exposed
- Planning purposes zero action tools
- Unknown purpose zero tools
- No silent fallback (error if tool in policy doesn't exist)

---

## Coverage requirement

95% for tool_exposure_enforcement.py.

---

## Validation commands

```bash
python -m pytest tests/test_tool_exposure_enforcement.py -q
python -c "
from runtime.tool_exposure_enforcement import get_allowed_tools
for p in ['intent_classifier', 'locator_specialist', 'execution_driver']:
  print(f'{p}: {get_allowed_tools(p)}')
"
```

---

## Artifact/evidence requirement

- [ ] `runtime/tool_exposure_enforcement.py` — enforcement logic
- [ ] Tool exposure per purpose verified
- [ ] 9+ tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references tool exposure

---


---

## Implementation evidence (Sprint 6 Cluster 2)

- **Commit:** 7491f35 — feat: enforce llm runtime context policies
- **Modules added/changed:** runtime/tool_exposure_enforcement.py
- **Tests:** tests/test_tool_exposure_enforcement.py
- **Test result:** 102 cluster tests passing, 1321 total suite passing (as of commit 7491f35)
- **Coverage:** runtime/context_policy.py, runtime/context_gates.py, runtime/context_request_policy.py, runtime/memory_selection_policy.py, runtime/tool_exposure_enforcement.py, runtime/schema_validation_policy.py, runtime/token_budget_policy.py covered via dedicated test files
- **Validation command:** `python -m pytest tests/test_context_policy.py tests/test_context_gates.py tests/test_context_request_policy.py tests/test_memory_selection_policy.py tests/test_tool_exposure_enforcement.py tests/test_schema_validation_policy.py tests/test_token_budget_policy.py -q` → 102 passed
- **Architecture invariant:** All context levels enforced via runtime/ modules; agent.py does not build ad-hoc context

## Stop conditions

- Tool definitions missing (verify all_tools registry)
- Existing tests fail
- Coverage below 95%

---

## Sign-off

- [x] Story focused (tool enforcement)
- [x] Tests verify no over-exposure
- [x] Planning purposes protected
