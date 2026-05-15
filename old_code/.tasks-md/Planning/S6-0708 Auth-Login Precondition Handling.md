# S6-0708 — Auth/Login Precondition Handling

## Story ID
S6-0708

## Objective
Handle cases where requested page/flow requires login or auth state.

## What it contains

- Auth_required classification and detection
- Manual login request with pause/resume
- Saved auth state option (if available)
- Fail-safe path if auth unavailable
- Precondition event contract with next-actions
- Integration with permission/risk policy (S6-0701, S6-0702)

## What it must NOT contain

- Actual login implementation (that's infrastructure)
- Credential storage (that's vault)
- Frontend login UI (that's app)
- Browser execution without permission

## Tests first

### Unit tests

- Dashboard request while logged out emits `auth_required`
- Auth_required classified as precondition, not error
- Manual login option offered with clear instructions
- Saved auth state option offered only if present/valid
- LLM does not invent credentials
- Auth check deterministic per page/context
- Timeout handling for manual login (user doesn't respond)

### Contract tests

- `auth_required` event includes page, required_auth_type, next_legal_actions
- Execution blocked until auth precondition resolved
- Manual login triggers pause event
- Resume must match same run_id/session_context
- Stale auth state rejected

## Integration tests

- Auth detection integrates with permission mode (S6-0701)
- Auth required triggers S6-0709 (human-in-loop) if manual login needed
- Saved auth state validated before use
- Failed auth attempts do not retry infinitely

## Acceptance criteria

- Auth_required classification clear and testable
- Manual login flow documented with user expectations
- Saved auth state validation logic defined
- Permission integration complete (S6-0701)
- 95% coverage on auth_preconditions.py
- Integration with permission/human-in-loop tested
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0701 (Permission), S6-0702 (Risk), S6-0703 (Capability)
- Blocks: S6-0709 (Human-in-loop), S6-0809 (Regression)

## Notes

- Auth is a precondition, not an error; must be communicated clearly
- Design for test environments: allow skipping auth in safe contexts
- Saved auth state critical for headless/CI runs
- Integration with S6-0710 (human-in-loop) for manual login pause/resume
