# S6-0802 — Deterministic Recovery First

## Story ID
S6-0802

## Objective
Try deterministic recovery before LLM recovery.

## What it contains

- Scroll into view / focus retry
- Locator revalidation with updated page state
- Stale-safe wait with retry logic
- Resolve page-state precondition (navigation, auth)
- Regenerate locator candidates from updated DOM
- Classify unsupported/permission/data cases without LLM

## What it must NOT contain

- LLM recovery (that's S6-0804)
- Browser execution beyond recovery attempts
- Permission enforcement (that's S6-0701)
- Frontend implementation

## Tests first

### Unit tests

- Hidden element tries scroll-into-view before LLM
- Stale locator revalidates with updated page state
- Wrong page/navigation failure → offer precondition options before LLM
- Missing data → ask user before LLM
- Element becomes visible after scroll → resume without LLM
- Locator revalidation returns new candidate list
- Recovery attempts logged in tried[]
- Deterministic recovery timeout prevents infinite retries

### Contract tests

- Deterministic attempts are logged in recovery event tried[]
- LLM recovery not called if deterministic recovery succeeds
- Failed deterministic recovery includes evidence of what was tried
- Unsupported/permission/data cases resolved without LLM

## Integration tests

- Deterministic recovery runs before recovery diagnoser (S6-0804)
- Successful deterministic recovery resumes execution (S6-0806)
- Failed deterministic recovery triggers LLM recovery or user decision
- Recovery state lifecycle updated correctly (S6-0805)

## Acceptance criteria

- Deterministic recovery covers scroll, revalidate, wait, precondition, locator regeneration
- No LLM calls in deterministic path
- All attempts logged and visible
- 95% coverage on deterministic_recovery.py
- Integration tests cover success and fallthrough paths
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0801 (Failure Classification)
- Blocks: S6-0803 (Recovery Packet), S6-0804 (Recovery Proposal), S6-0806 (Resume)

## Notes

- Deterministic recovery must complete or timeout within ~5 seconds
- Evidence of failed deterministic attempts critical for recovery diagnoser
- Design for performance: retry logic should not multiply DOM queries
- Scenario spec requires deterministic-first before LLM
