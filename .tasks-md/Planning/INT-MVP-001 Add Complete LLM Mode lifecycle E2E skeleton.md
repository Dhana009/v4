# INT-MVP-001 Add Complete LLM Mode lifecycle E2E skeleton

Status: Planning  
Sprint: Sprint 2  
Type: Story  
Owner: E2E / Evidence  
Priority: P0  

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

## Evidence

TBD after implementation.
