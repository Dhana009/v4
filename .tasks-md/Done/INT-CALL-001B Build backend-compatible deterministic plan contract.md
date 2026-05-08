# INT-CALL-001B Build backend-compatible deterministic plan contract

Status: Done
Sprint: Sprint 3
Type: Story
Owner: Backend / LLM Runtime
Priority: P0
Started: 2026-05-08 20:11 IST

## Problem

deterministic_fast_path.py can classify simple flows but build_deterministic_plan() returns a flat plan. Backend execution expects a parent step with children.

## Source / architecture rule

- runtime/deterministic_fast_path.py
- agent.py
- _build_confirmed_execution_plan contract
- Backend Event Contract
- Complete LLM Mode Runtime Policy Spec

## Scope

Update build_deterministic_plan() to emit backend-compatible plan_ready payload:

Parent step:
- step_id
- intent
- expected_outcome
- status
- kind
- type
- children[]

Child operation:
- operation_id
- type
- description
- target
- locator
- status
- assertion/value/expected_value when relevant

## Out of scope

- Executing the plan
- Bypassing confirmation
- Broad agent.py rewrite

## Required tests

- deterministic click plan has parent + children
- deterministic visible assertion plan has assertion child
- deterministic exact text plan has expected_value child
- output shape is compatible with _build_confirmed_execution_plan expectations

## Acceptance criteria

- deterministic plan can be consumed by backend execution-contract builder
- no browser action happens here
- tests pass

## Cost-aware verification plan

Run deterministic fast path and backend plan contract unit tests only.
No E2E.

## Evidence

- `python -m py_compile runtime/deterministic_fast_path.py tests/test_deterministic_fast_path.py` -> passed
- `python -m pytest tests/test_deterministic_fast_path.py -q` -> 24 passed

## Implementation summary

- `build_deterministic_plan()` now emits a backend-compatible `plan_ready` payload with a parent step and normalized `children`
- deterministic children now carry `operation_id`, `type`, `description`, `target`, `locator`, `status`, and `assertion` or `value` or `expected_value` where relevant
- focused tests now prove click, fill, visible assertion, exact-text assertion, and compatibility with `AgentLoop._build_confirmed_execution_plan()`

## Notes

This is the missing structure that blocks the live fast path.
