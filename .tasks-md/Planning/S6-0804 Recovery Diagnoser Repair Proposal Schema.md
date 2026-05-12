# S6-0804 — Recovery Diagnoser Repair Proposal Schema

## Story ID
S6-0804

## Objective
Complete `recovery_diagnoser` output schema and backend validation before execution.

## Allowed outputs

```
repair_proposal
ask_user
capability_gap
stop
```

## Repair proposal contract

```
target_operation_id
repair_type (locator|action|navigation|wait|precondition|data)
locator_correction
action_modification
navigation_target
wait_condition
precondition_resolution
expected_after_repair
repair_reasoning
confidence_level
```

## What it contains

- Recovery diagnoser prompt and policy
- Output schema validation (must be one of 4 types)
- Repair proposal validator (integrity checks)
- Backend execution validation (repairs are executable)
- Intent-change detection (repair that changes user goal)
- Fallback to ask_user or stop if repair invalid

## What it must NOT contain

- Repair execution (that's S6-0806)
- LLM training/fine-tuning
- Frontend implementation
- Permission logic (S6-0701)

## Tests first

### Unit tests

- Repair proposal must target failed_operation_id
- Repair cannot change user goal silently
- Repair proposal includes confidence level
- Unsupported repair → `capability_gap` (not fake success)
- Ambiguous repair → `ask_user` with clear clarification question
- Invalid schema → retry once then `stop` (fail-closed)
- Stop reason included and clear
- Output validation 100% deterministic

### Contract tests

- recovery_diagnoser cannot emit `recorded` or `completed` states
- Repair proposal requires backend validation before execution (S6-0806)
- Intent-changing repair requires user confirmation
- Repair schema matches allowed types
- Output immutable after validation

## Integration tests

- Recovery diagnoser called with packet from S6-0803
- Output validation integrates with recovery lifecycle (S6-0805)
- Repair proposals flow to executor (S6-0806)
- Ask_user and stop paths halt execution safely

## Acceptance criteria

- Recovery diagnoser prompt fully specified and tested
- Output schema validation 100% deterministic
- Intent-change detection comprehensive
- Fallback to ask_user or stop if invalid
- 95% coverage on recovery_proposal_schema.py
- Backend validation contract documented
- Integration tests cover all four output paths
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0802 (Deterministic Recovery), S6-0803 (Recovery Packet)
- Blocks: S6-0805 (Lifecycle), S6-0806 (Resume), S6-0807 (User Guidance)

## Notes

- Repair must target failed operation; no scope creep to other operations
- Intent-change must be explicit user decision (S6-0807)
- Fail-closed default: if repair invalid, ask user or stop
- Scenario spec requires repair validation and bounded recovery
