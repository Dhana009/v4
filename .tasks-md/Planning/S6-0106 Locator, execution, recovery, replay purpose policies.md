# S6-0106 Locator, execution, recovery, replay purpose policies

**Sprint:** Sprint 6  
**Cluster:** 1 (LLM Runtime Purpose Coverage)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Runtime Policy  
**Blocks:** S6-0107  
**Blocked by:** S6-0105  

---

## Purpose

Complete policies for 4 operational purposes: locator_specialist (locator discovery), execution_driver (action execution), recovery_diagnoser (failure recovery), replay_repair_specialist (replay repair). These are execution-critical; tool exposure must be strictly bounded.

---

## Source rules

- Runtime Policy Spec: locator_specialist gets locator/context tools only
- Runtime Policy Spec: execution_driver gets only next confirmed operation tool
- Runtime Policy Spec: execution_driver blocked outside executing phase
- Runtime Policy Spec: recovery_diagnoser cannot emit recorded/completed operations
- Runtime Policy Spec: replay_repair_specialist outputs repair diff only
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/llm_purpose_registry.py` — registry (from S6-0102)
- `runtime/llm_purpose_policy.py` — 9 purposes so far
- `locator/engine.py` — locator logic (test: test_dom_locator_contracts.py)
- `recording/replay.py` — replay logic (test: test_replay_one.py)
- Sprint 5: execution_driver contract tests referenced but may be minimal

### What gaps exist

- No explicit policy metadata for 4 operational purposes
- No schema for locator specialist output (ranked candidates)
- No schema for execution driver (next operation confirmation)
- No schema for recovery diagnoser (diagnostic output + fallback action)
- No schema for replay repair (repair diff)
- No tests for these policies

---

## Desired behavior

### Purpose details

**locator_specialist**
- Input: page state, target element ambiguity
- Output: ranked locator candidates {selector, confidence, strategy, alternative}
- Schema: ranked list, confidence numeric
- Validator: all candidates have confidence score, selector syntax valid
- Tools: locator tools + inspection/read-only, no action tools
- Constraint: cannot recommend execution
- Fallback: ask_user for clarification

**execution_driver**
- Input: confirmed next operation from plan
- Output: execution result + status
- Schema: {operation_id, status: success|failed|skipped, result_summary}
- Validator: operation_id stable, status in enum
- Tools: only next_operation tool (from controller constraint)
- Constraint: only available during executing phase, cannot claim non-confirmed operation
- Fallback: skip operation, mark as skipped

**recovery_diagnoser**
- Input: failed operation, error evidence
- Output: diagnostic {root_cause, recommendation}
- Schema: structured diagnostic, includes recommendation
- Validator: recommendation is one of {retry, alternate_locator, clarify, escalate}
- Tools: diagnostic/context tools only, no execution, no recording mutation
- Constraint: cannot emit recorded_step or completed events
- Fallback: escalate to user

**replay_repair_specialist**
- Input: replay failure, original vs actual states
- Output: repair diff {changes to recording}
- Schema: structured diff {operation_id, field, old_value, new_value}
- Validator: cannot drop operations, cannot reorder
- Tools: inspection/read-only, no execution, no direct replay mutation
- Constraint: repair diff is proposal only
- Fallback: mark replay as unfixable

---

## Out of scope

- Do not implement browser recovery E2E
- Do not implement full replay repair product flow
- Do not broaden execution tool permissions
- Do not run paid LLM

---

## Allowed files

- `runtime/llm_purpose_policy.py` (modify: add 4 purposes)
- `runtime/llm_purpose_registry.py` (modify: add to registry)
- `runtime/operational_purpose_validator.py` (new, if modular)
- `tests/test_operational_purpose_policies.py` (new)

---

## Forbidden files

- ✗ locator/engine.py (no logic changes)
- ✗ recording/replay.py (no logic changes)
- ✗ agent.py (no orchestration changes)
- ✗ frontend/

---

## Tests first

### Unit tests

- `test_locator_specialist_schema_is_ranked_list()`
- `test_locator_specialist_confidence_is_numeric()`
- `test_locator_specialist_forbids_action_tools()`
- `test_execution_driver_schema_valid()`
- `test_execution_driver_forbids_unconfirmed_operation()`
- `test_execution_driver_forbids_tools_outside_executing_phase()`
- `test_recovery_diagnoser_forbids_recording_mutation()`
- `test_recovery_diagnoser_recommendation_in_enum()`
- `test_replay_repair_forbids_operation_drop()`
- `test_replay_repair_forbids_operation_reorder()`

### Contract tests

- `test_locator_specialist_policy_in_registry()`
- `test_execution_driver_policy_in_registry()`
- `test_recovery_diagnoser_policy_in_registry()`
- `test_replay_repair_specialist_policy_in_registry()`
- `test_existing_locator_contract_tests_still_pass()`
- `test_existing_replay_contract_tests_still_pass()`

File: `tests/test_operational_purpose_policies.py`

---

## Implementation notes

### Approach

1. Define 4 purpose policies with strict tool/schema constraints
2. Create schemas:
   - Locator: list of {selector, confidence, strategy}
   - Execution: {operation_id, status enum, result}
   - Recovery: {root_cause, recommendation enum}
   - Replay repair: {changes list with operation_id, field, values}
3. Create validators:
   - Locator: confidence is 0–1, selector syntax valid
   - Execution: status in enum, operation_id present
   - Recovery: recommendation in {retry, alternate_locator, clarify, escalate}
   - Repair: all changes reference existing operations
4. Add to registry with strict tool constraints
5. Write 10+ tests
6. Verify existing locator and replay tests still pass

### Key invariants

- locator_specialist has zero action tools
- execution_driver can only execute confirmed operations
- recovery_diagnoser cannot mutate recording
- replay_repair outputs proposal only
- All schemas are strict (fail on prose)

---

## Coverage requirement

95% for new validators.

---

## Validation commands

```bash
python -m pytest tests/test_operational_purpose_policies.py -q
python -m pytest tests/test_dom_locator_contracts.py tests/test_replay_one.py -q  # Must pass
python -c "
from runtime.llm_purpose_registry import PURPOSE_REGISTRY
for p in ['locator_specialist', 'execution_driver', 'recovery_diagnoser', 'replay_repair_specialist']:
  policy = PURPOSE_REGISTRY.get(p)
  print(f'{p}: tools={policy.tool_policy}')
"
```

---

## Artifact/evidence requirement

- [ ] 4 operational purpose policies in registry
- [ ] Schemas for each purpose (ranked, status, diagnostic, diff)
- [ ] Validators for each
- [ ] 10+ tests passing
- [ ] Locator contract tests still pass
- [ ] Replay contract tests still pass
- [ ] Coverage ≥95%
- [ ] Commit message references 4 operational purposes

---

## Stop conditions

- Locator or replay tests fail (cannot proceed)
- Cannot define clear tool boundary for execution_driver
- Cannot distinguish valid repairs from invalid (operation drops/reorders)
- Coverage below 95%

---

## Sign-off

- [x] Story focused (4 operational purposes)
- [x] Tests verify strict tool/schema constraints
- [x] Existing locator/replay behavior preserved
- [x] No execution tool over-exposure
