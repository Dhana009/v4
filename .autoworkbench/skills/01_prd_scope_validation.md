# Skill: PRD Scope Validation

## Purpose
Ensure every implementation task is grounded in the PRD and current approved specs before coding.

## When to use
Use before starting any Codex task, especially architecture, backend lifecycle, LLM runtime, frontend UI, replay, locator, codegen, or tests.

## Source of truth
Use this priority:
1. PRD v2.3 modular pack
2. Approved Complete LLM Mode architecture spec
3. Approved Frontend/UI spec
4. Approved LLM Runtime Policy spec
5. Handoff notes and regression findings
6. Current implementation

## Non-negotiable rules
1. Do not implement from intuition alone.
2. Do not treat existing broken code as source of truth.
3. Do not start V2/broad features before the current scoped phase is accepted.
4. If PRD and implementation conflict, report the conflict before changing behavior.
5. If PRD is unclear, stop and ask for clarification instead of guessing.
6. If a requested change changes product architecture, call it out explicitly.
7. Do not change architecture from intuition.

## Required implementation behavior
Before code changes:
- Identify the feature area.
- Find the relevant PRD/spec requirement.
- Summarize expected behavior in 3–6 bullets.
- Inspect current implementation.
- Compare expected vs actual.
- Classify the task as:
  - bug fix
  - contract implementation
  - refactor without behavior change
  - test harness work
  - UI rendering change
  - LLM runtime policy change
  - capability addition
- Define acceptance criteria before implementation.

## Required tests
Choose tests based on scope:
- backend unit tests for runtime rules
- contract tests for typed events/commands
- frontend tests/build checks for UI state rendering
- E2E tests for real product flows
- regression tests for any bug found

## Verification commands
Use focused commands only first:
```bash
python -m pytest <focused-tests> -q
npm run build
```
Run broader suites only after focused tests pass.

## Stop conditions
Stop and report if:
- required evidence is missing, unclear, or contradictory
- no relevant PRD/spec section exists
- task requires changing approved architecture
- acceptance criteria are unclear
- current code has multiple possible root causes and evidence is insufficient
- implementation would require touching many unrelated modules

## Reporting format
Report:
1. PRD/spec sections inspected
2. Expected behavior
3. Current behavior
4. Root cause or gap
5. Proposed narrow implementation
6. Tests planned
7. Risks/stop conditions
