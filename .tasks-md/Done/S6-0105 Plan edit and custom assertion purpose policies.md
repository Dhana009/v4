# S6-0105 Plan edit and custom assertion purpose policies

**Sprint:** Sprint 6  
**Cluster:** 1 (LLM Runtime Purpose Coverage)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0106, S6-0107  
**Blocked by:** S6-0104  

---

## Purpose

Complete policy for 2 plan-modifying purposes: plan_diff_editor (proposal-only), custom_assertion_planner (assertion builder). Both must forbid direct execution/mutation and expose inspection tools only.

---

## Source rules

- Runtime Policy Spec: plan_diff_editor receives active plan context only, proposes changes
- Runtime Policy Spec: plan_diff_editor cannot silently drop/reorder operations
- Runtime Policy Spec: custom_assertion_planner uses inspection/context tools only
- Runtime Policy Spec: custom_assertion_planner asks user when expected value missing
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/llm_purpose_registry.py` — registry (from S6-0102)
- `runtime/llm_purpose_policy.py` — 7 purposes so far (from S6-0103, S6-0104)
- Plan correction framework (Sprint 5, not yet detailed in tests)

### What gaps exist

- No policy for plan_diff_editor (new in Phase 5 plan discussion)
- No policy for custom_assertion_planner (new, assertion builder)
- No schema for plan diffs (change sets)
- No schema for custom assertions
- No tests for these purposes

---

## Desired behavior

### Purpose details

**plan_diff_editor**
- Input: active plan, user edit request
- Output: diff (set of {op: add/modify/remove, target, value})
- Schema: structured diff, must reference all modified operations
- Validator: each diff operation valid, no silent drops/reorders
- Tools: inspection/read-only only, no execution
- Constraint: cannot mutate plan directly; only proposes changes to user
- Fallback: ask_user for confirmation

**custom_assertion_planner**
- Input: execution result, assertion requirement
- Output: assertion (selector, expected_value, operator)
- Schema: structured assertion
- Validator: all required fields present, expected value non-empty or marked as user_input_required
- Tools: inspection/context tools only, no execution/locator
- Fallback: ask_user for missing expected value

---

## Out of scope

- Do not implement plan correction flow (frontend edit/submit)
- Do not implement assertion UI
- Do not expand assertion capability framework
- Do not run paid LLM

---

## Allowed files

- `runtime/llm_purpose_policy.py` (modify: add 2 purposes)
- `runtime/llm_purpose_registry.py` (modify: add to registry)
- `runtime/plan_edit_validator.py` (new, if modular)
- `tests/test_plan_edit_purpose_policies.py` (new)

---

## Forbidden files

- ✗ agent.py (no flow changes)
- ✗ frontend/ (no UI yet)
- ✗ Plan correction/assertion modules (behavioral changes deferred)

---

## Tests first

### Unit tests

- `test_plan_diff_editor_schema_is_structured()`
- `test_plan_diff_editor_forbids_direct_mutation()`
- `test_plan_diff_editor_forbids_tools()`
- `test_plan_diff_forbids_silent_operation_drop()`
- `test_custom_assertion_planner_schema_valid()`
- `test_custom_assertion_planner_forbids_tools()`
- `test_custom_assertion_expected_value_required_or_marked_user_input()`

### Contract tests

- `test_plan_diff_editor_policy_in_registry()`
- `test_custom_assertion_planner_policy_in_registry()`
- `test_plan_diff_editor_diff_is_proposal_not_mutation()`
- `test_custom_assertion_marks_missing_expected_as_user_input()`

File: `tests/test_plan_edit_purpose_policies.py`

---

## Implementation notes

### Approach

1. Define policy for each 2 purposes (similar structure to earlier)
2. Create schema:
   - Diff: {op: "add"|"modify"|"remove", target_step_id, value}
   - Assertion: {selector, expected_value (or null + user_input_required), operator}
3. Create validators:
   - Diff: check op is valid, target exists in plan, value is provided
   - Assertion: check selector and operator are valid, expected_value provided or marked user_input_required
4. Add to registry (tools exposed strictly)
5. Write 7+ tests
6. Ensure no behavioral changes to plan correction (yet)

### Key invariants

- plan_diff_editor has zero tools (inspection built into controller, not LLM)
- plan_diff_editor cannot claim to have mutated plan
- custom_assertion_planner forbids execution tools
- Both require user confirmation before mutation

---

## Coverage requirement

95% for validators.

---

## Validation commands

```bash
python -m pytest tests/test_plan_edit_purpose_policies.py -q
python -c "
from runtime.llm_purpose_registry import PURPOSE_REGISTRY
for p in ['plan_diff_editor', 'custom_assertion_planner']:
  print(f'{p}: tools={len(PURPOSE_REGISTRY.get(p).tool_policy)}')
"
```

---

## Artifact/evidence requirement

- [ ] 2 purpose policies in registry
- [ ] Schema for each purpose (diff, assertion)
- [ ] Validators for each
- [ ] 7+ tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references plan edit/assertion

---

## Stop conditions

- Cannot define clear diff schema
- Cannot distinguish valid assertions from invalid
- Coverage below 95%

---

## Sign-off

- [x] Story focused (2 plan-modifying purposes)
- [x] Tests verify proposal-only (no mutation)
- [x] Tools strictly limited
