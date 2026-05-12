# S6-0709 — Long-Running Async Result Strategy

## Story ID
S6-0709

## Objective
Support flows where results take time to complete, such as resume analysis or report generation.

## What it contains

- Wait strategy metadata (poll interval, total timeout, backoff)
- Timeout policy and handling
- Progress feedback event
- Cancel/extend options for long-running operations
- Integration with assertion/validation logic (no premature assertion failure)
- Event contract for wait completion

## What it must NOT contain

- Actual async execution (that's browser context)
- Indefinite waiting without timeout
- Frontend progress UI (that's app)
- Browser execution without permission

## Tests first

### Unit tests

- Long-running result capability declares wait strategy
- Wait strategy includes timeout, poll interval, max retries
- Timeout emits recoverable failure with next actions
- Timeout does not cascade to unrelated operations
- Cancel/extend options are generated and valid
- Wait state tracked per operation
- Multiple long-running operations can be concurrent

### Contract tests

- Plan includes wait/postcondition metadata for async operations
- Assertion does not run before wait condition satisfied
- Wait timeout event includes waited_for, max_wait, actual_wait
- Stale wait instruction rejected
- Long-running operation cannot block entire run

## Integration tests

- Wait strategy integrates with permission modes (S6-0701)
- Progress event flows to user (S6-0710 human-in-loop)
- Cancel/extend options visible in run state
- Recovery policy (S6-0802) handles wait timeouts

## Acceptance criteria

- Wait strategy schema fully defined
- Timeout handling for all async scenarios
- Progress events emit periodically with ETA
- Cancel/extend options fully functional
- 95% coverage on long_running_policy.py
- Integration tests cover timeout, success, cancel, extend paths
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0701 (Permission), S6-0702 (Risk)
- Blocks: S6-0710 (Human-in-loop), S6-0802 (Deterministic Recovery)

## Notes

- Resume analysis, report generation, payment processing typical long-running scenarios
- Design for observability: progress events allow user to monitor without polling
- Timeout is not failure; triggers recovery or human decision (S6-0710)
- Scenario spec requires no premature assertion on async results
