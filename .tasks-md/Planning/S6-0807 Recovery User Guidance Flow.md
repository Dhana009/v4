# S6-0807 — Recovery User Guidance Flow

## Story ID
S6-0807

## Objective
Handle user-provided recovery instruction safely.

## What it contains

- Recovery instruction classification (retry|skip|stop|clarification_needed)
- Ask one precise clarification if ambiguous
- Apply only to failed step unless user explicitly changes scope
- Validate instruction before retry
- Scope validation (instruction applies to current step only)

## What it must NOT contain

- Permission enforcement (S6-0701)
- Recovery diagnosis (S6-0804)
- Frontend interaction UI (that's app)
- Credential/secret collection

## Tests first

### Unit tests

- "try the second button" applies to failed operation (not others)
- "skip this step" marks skipped with reason
- "stop" stops run and records terminal state
- Ambiguous "fix it" asks one clarification question
- Instruction classification deterministic
- Scope change explicitly required (not implicit)
- Invalid scope rejected with clear message
- Stale instruction (from old run) rejected

### Contract tests

- User recovery instruction includes run_id/step_id/operation_id
- Scope-changing instruction requires explicit confirmation
- Instruction validation happens before execution attempt
- Rejected instruction does not cause retry loop

## Integration tests

- User guidance integrates with recovery lifecycle (S6-0805)
- User clarification request includes options (not open-ended)
- Instruction flows to recovery executor (S6-0806)
- Terminal instructions (skip/stop) update recovery state correctly

## Acceptance criteria

- Instruction classifier covers retry, skip, stop, clarification cases
- Scope validation strict and fail-safe
- One clarification maximum per instruction
- Stale instruction rejection working
- 95% coverage on recovery_instruction_policy.py
- Integration tests cover all classification paths
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0805 (Lifecycle), S6-0804 (Recovery Proposal)
- Blocks: S6-0808 (Integration), S6-0809 (Regression)

## Notes

- User instruction is explicit repair, not LLM-guessed intent
- Scope validation critical: instruction cannot accidentally affect other steps
- Design for clarity: ask one clear question, not multiple choice
- Scenario spec requires user instruction scoped and validated
