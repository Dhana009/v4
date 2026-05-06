# Skill: TDD and Regression Harness

## Purpose
Enforce test-first development and prevent “tests pass but product fails” regressions.

## When to use
Use for every implementation task. Mandatory when touching backend runtime, frontend UI, LLM controller, locator flow, replay, recording, codegen, or E2E harness.

## Source of truth
- PRD acceptance criteria
- Complete LLM Mode specs
- Existing regression bugs/handoff notes
- Real-world fixture strategy

## Non-negotiable rules
1. Define or write the failing test before implementation whenever practical.
2. Do not rely only on unit tests for browser/ui host behavior.
3. E2E failures must fail at named stages, not generic long timeouts.
4. Tests must capture logs/artifacts needed for diagnosis.
5. Avoid toy-only fixtures for real-world behavior.
6. If a test is flaky, identify why; do not simply increase timeout.
7. All new UI controls important to E2E must have stable selectors/data-testid where applicable.
8. Do not let tests redefine architecture or backend truth by convenience.

## Required implementation behavior
For each task:
- Define acceptance criteria.
- Add/adjust focused failing tests.
- Implement smallest change.
- Run focused tests.
- Capture artifacts on E2E failure.
- Report exact failing stage if any.
- Add regression coverage for root cause, not only symptom.

## Required test levels
Use the relevant levels:
- Backend unit tests
- Backend integration/contract tests
- Frontend build/component-state tests where available
- Browser-driven E2E tests
- Shadow DOM-aware E2E tests when UI host is involved
- Real-world fixture tests for locator/DOM behavior

## E2E harness requirements
E2E harness should capture:
```text
backend stdout/stderr
frontend console logs
page HTML on failure
screenshot on failure
failure-context.json
stage name
last successful stage
LLM triggered true/false
backend markers present/missing
artifact path
```

## Stage-aware failure examples
Use stages like:
```text
backend_started
ui_host_ready
shadow_host_ready
steps_created
locator_validated
plan_ready_seen
execution_started
step_recorded_seen
code_update_seen
trace_event_seen
```

## Verification commands
Examples:
```bash
python -m pytest tests/<focused_test>.py -q
python -m pytest tests/e2e/<focused_flow>.py -q -s
npm run build
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- test cannot observe the behavior
- failure has no artifacts
- E2E is waiting without knowing current stage
- test depends on live external site without fixture fallback
- passing test does not prove product behavior

## Reporting format
Report:
1. Tests added/updated
2. Expected initial failure if TDD
3. Implementation summary
4. Commands run
5. Results
6. Artifact paths
7. Last successful E2E stage
8. Remaining risks
