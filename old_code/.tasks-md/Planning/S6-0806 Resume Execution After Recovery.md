# S6-0806 — Resume Execution After Recovery

## Story ID
S6-0806

## Objective
Resume from the failed step/operation safely without contaminating other steps.

## What it contains

- Strict operation cursor (cannot jump to unrelated step)
- Repaired operation validation (executes only after backend evidence)
- Continue from current browser state (use saved page state if available)
- Preserve previous successful operations (no rerun unless required)
- Update only failed operation if repair succeeds
- Evidence attachment to same parent step

## What it must NOT contain

- Permission logic (S6-0701)
- Recovery diagnosis (S6-0804)
- Frontend implementation
- LLM recovery (S6-0804)

## Tests first

### Unit tests

- Repair resumes at failed_operation_id exactly
- Prior successful operations are not rerun
- Later operations wait until failed operation resolved
- Repaired operation evidence attached to same step
- Cannot jump to unrelated operation (cursor check fails)
- Execute only after validation succeeds
- Browser state preserved between failed and repaired execution
- Operation result (success/failure) recorded

### Contract tests

- LLM cannot jump to unrelated step
- Repaired result records only after backend execution evidence (locator found, action executed)
- Step evidence includes original failure + repair + success/failure
- Cursor enforcement immutable

## Integration tests

- Resume executor called after repair_validated state (S6-0805)
- Browser context state preserved across pause/resume
- Execution continues with remaining planned operations
- Failure on repaired operation triggers new recovery cycle

## Acceptance criteria

- Operation cursor enforcement strict and testable
- Repaired operation executes in correct order
- Prior successful operations preserved
- Browser state persistence across pause/resume working
- 95% coverage on recovery_resume.py
- Integration tests cover success, failure, jump-attempt paths
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0804 (Recovery Proposal), S6-0805 (Lifecycle)
- Blocks: S6-0808 (Integration Proof), S6-0809 (Regression)

## Notes

- Strict operation cursor critical: prevents accidental scope creep
- Browser state preservation essential for headless runs
- Evidence attachment ensures full trace of failure → repair → result
- Design for auditability: resume operation logged with all context
