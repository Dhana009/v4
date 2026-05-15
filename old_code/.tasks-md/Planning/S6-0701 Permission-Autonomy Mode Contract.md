# S6-0701 — Permission/Autonomy Mode Contract

## Story ID
S6-0701

## Objective
Define and enforce permission modes: `strict`, `balanced`, `auto`.

## What it contains

- Permission mode model with three explicit modes
- Risk classification input
- Action permission decision logic
- Allowed next actions per mode
- Permission decision trace payload with reason/risk/choices

## What it must NOT contain

- Browser execution
- Frontend visual implementation
- Destructive action support
- Broad agent.py refactor

## Tests first

### Unit tests

- `strict` mode asks before every browser-changing action
- `balanced` mode allows safe actions, asks for high-risk actions
- `auto` mode runs confirmed safe/medium plan, asks for destructive/high-risk
- Read/assert actions do not require permission
- Permission mode can be queried from runtime context
- Invalid permission mode rejected with safe default

### Contract tests

- `permission_required` event includes risk_level, operation, reason, choices
- Permission decision tied to run_id/step_id/operation_id
- Stale permission decision (old run_id) rejected
- Permission grant scoped to single operation by default unless explicit blanket grant

### Integration tests

- Permission modes can be set before runtime init
- Runtime respects permission mode throughout execution context
- Mode can be overridden per-request if allowed
- Trace includes all permission decisions

## Acceptance criteria

- Three permission modes fully specified and testable
- Contract events match S6-0001 Requirement-to-Test Matrix
- 95% coverage on new modules
- No browser/frontend code mixed in
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0702 (Risk Classification)
- Blocks: S6-0708, S6-0709

## Notes

- Permission mode is system-level or per-run context, not per-action config
- `strict` = maximum control; `auto` = maximum autonomy (within risk bounds)
- `balanced` is the recommended default for production workflows
- Design for runtime introspection: `runtime.permission_mode()` and `runtime.allowed_next_actions()`
