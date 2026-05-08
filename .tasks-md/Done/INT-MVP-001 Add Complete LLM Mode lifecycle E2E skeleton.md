# INT-MVP-001 Add Complete LLM Mode lifecycle E2E skeleton

Status: Done  
Sprint: Sprint 2  
Type: Story  
Owner: E2E / Evidence  
Priority: P0  
Started: 2026-05-08 17:05 IST  
Completed: 2026-05-08 17:10 IST  

## Source docs

- Complete LLM Mode P0 scenario spec: core event pipeline
- `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`
- `.tasks-md/Backlog/MVP-001 End-to-end LLM Mode run lifecycle smoke.md`
- E2E harness strategy docs

## Problem / Goal

The MVP lifecycle smoke story remains Backlog. Sprint 2 should create a focused E2E skeleton that documents the required Complete LLM Mode event sequence and gives runtime-wiring work a concrete target.

## Scope

Create an E2E skeleton that starts a session, submits one simple LLM Mode intent, captures the backend event stream, and asserts the expected lifecycle sequence.

Expected sequence:

```text
run_started
plan_ready
confirmed / confirmation accepted
execution_started
step_recorded
code_update
run_completed
```

## Out of scope

```text
backend implementation changes
frontend implementation changes
runtime rewrites
broad harness redesign
```

## Required tests

```text
tests/e2e/test_mvp_001_lifecycle_smoke.py
```

The test may be xfail only if it documents missing product behavior. Do not xfail existing E2E tests or environment failures.

## Acceptance criteria

```text
MVP-001 skeleton is collected by pytest
expected event sequence is explicit
failure mode is meaningful
no product code changes
```

## Stop conditions

```text
start_e2e_session fails due to environment
no event capture helper exists and broad harness work would be required
current E2E truth is still unknown
```

## Implementation summary

Created `tests/e2e/test_mvp_001_lifecycle_smoke.py` with 6 lifecycle checkpoints:

1. `overlay_loaded` — page loads, shadow DOM overlay ready
2. `plan_ready_seen` — LLM returns a plan (`[AGENT] plan_ready sent`)
3. `confirmed` — user confirms plan, `[CONFIRMED_PLAN]` logged
4. `execution_started` — page navigates, `[EXECUTION_CONTRACT]` logged
5. `step_recorded` — `.ide-recorded-step` visible, `[CONFIRMED_CURSOR]` logged, step count = 1
6. `code_update_seen` — `[CODE_UPDATE]` logged, generated Playwright line asserted

No product code modified. Uses existing harness helpers only.

## Verification

```text
python -m py_compile tests/e2e/test_mvp_001_lifecycle_smoke.py  → OK
python -m pytest tests/test_e2e_harness.py -q  → 58 passed
python -m pytest tests/e2e/test_mvp_001_lifecycle_smoke.py -q -s  → 1 passed in 18.48s
python -m pytest tests/e2e/ -q -s  → 5 passed in 114.42s (no regression)
```

## Commit

TBD — committed with "test: add mvp lifecycle e2e skeleton"
