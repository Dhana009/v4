# S6-0710 — Human-In-Loop Flow

## Story ID
S6-0710

## Objective
Support OTP, captcha, manual login, file chooser, or blocked automation steps.

## What it contains

- `human_input_required` event contract
- Expected input type classification
- Resume conditions and validation
- Timeout and cancel options
- Trace entry for human-provided input
- Integration with permission/precondition logic (S6-0701, S6-0708)

## What it must NOT contain

- Frontend input UI (that's app)
- Credential collection (that's separate flow with secrets)
- Browser automation of human-blocked steps
- Indefinite waiting without timeout

## Tests first

### Unit tests

- OTP request emits `human_input_required` with type `otp_code`
- Captcha emits `cannot_automate` or `human_input_required` with type `captcha_solve`
- Manual login pauses execution safely with clear instructions
- User-provided input is validated before resume
- Input timeout triggers cancel/fallback
- Resume condition checks match paused step
- Multiple human inputs can be queued in single run

### Contract tests

- `human_input_required` includes step_id, operation_id, input_type, expected_format, timeout_seconds
- LLM cannot bypass human-required state
- `run_completed` blocked while human input pending
- User input resumes only correct step (no cross-step resumption)
- Stale human input (from old run) rejected

## Integration tests

- Human input detection integrates with capability registry (S6-0703)
- Human input pause/resume works with permission modes (S6-0701)
- Long-running timeout (S6-0709) can trigger human input
- Recovery policy (S6-0802) respects human input pause state

## Acceptance criteria

- `human_input_required` event fully specified
- Input type classification covers OTP, captcha, manual interaction, file chooser
- Resume validation deterministic and fail-safe
- Timeout handling with user notification
- 95% coverage on human_input_contracts.py
- Integration tests cover OTP, captcha, manual-login, file-chooser scenarios
- Pause/resume state persists safely
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0701 (Permission), S6-0703 (Capability), S6-0708 (Auth), S6-0709 (Long-running)
- Blocks: S6-0809 (Regression)

## Notes

- Human-in-loop is a precondition, not an error
- Design for timeout safety: clear fallback if user doesn't respond
- Trace entry critical for audit and replay decisions
- Integration with S6-0702 (risk) ensures human input is always required, never optional
