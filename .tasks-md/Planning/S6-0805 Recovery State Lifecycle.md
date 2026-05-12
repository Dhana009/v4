# S6-0805 — Recovery State Lifecycle

## Story ID
S6-0805

## Objective
Ensure recovery state blocks completion and recording until resolved.

## Recovery state transitions

```
recovery_needed
recovery_pending (deterministic attempt in progress)
repair_proposed (LLM diagnoser output received)
repair_validated
execution_resumed
step_skipped
run_failed
recovery_resolved
```

## What it contains

- Recovery state machine implementation
- State transition validation (no invalid transitions)
- Blocking conditions (run_completed blocked while recovery open)
- Recording/code_update blocking (until recovery resolved)
- State event emission on every transition
- Stale recovery instruction rejection

## What it must NOT contain

- Recovery execution (that's S6-0806)
- LLM recovery logic (that's S6-0804)
- Frontend state UI (that's app)
- Permission logic (S6-0701)

## Tests first

### Unit tests

- recovery_needed → recovery_pending (deterministic start)
- recovery_pending → repair_proposed (LLM output) or recovery_needed (retry)
- repair_proposed → repair_validated (validation pass)
- repair_validated → execution_resumed (resume)
- execution_resumed → recovery_resolved (step success)
- Alternative: repair_validated → step_skipped (user skip)
- Alternative: repair_validated → run_failed (user/policy stop)
- Recovery open blocks run_completed event
- Unresolved failed step cannot record
- Unresolved failed step cannot emit code_update
- Skip step marks skipped with reason
- Stop run emits terminal failed/stopped state
- State transitions immutable once completed

### Contract tests

- Lifecycle events emitted in valid order only
- Duplicate recovery resolution rejected
- Stale recovery instruction (old run_id) rejected
- Events include context (run_id, step_id, operation_id)

## Integration tests

- Recovery lifecycle integrates with deterministic recovery (S6-0802)
- Recovery lifecycle integrates with repair execution (S6-0806)
- Recovery lifecycle integrates with user guidance (S6-0807)
- Recording system respects blocking conditions

## Acceptance criteria

- State machine fully specified and tested
- All state transitions documented
- Blocking conditions for completion/recording enforced
- Skip/stop paths terminate recovery safely
- 95% coverage on recovery_lifecycle.py
- Integration tests verify blocking and state flow
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0801 (Failure Classification), S6-0802 (Deterministic Recovery), S6-0804 (Recovery Proposal)
- Blocks: S6-0806 (Resume), S6-0807 (User Guidance), S6-0809 (Regression)

## Notes

- State machine is critical gating point: no escape from recovery state
- Blocking conditions prevent partial/incomplete results from being recorded
- Design for visibility: all state transitions logged for audit
- Scenario spec requires no unresolved failed step can record/code_update
