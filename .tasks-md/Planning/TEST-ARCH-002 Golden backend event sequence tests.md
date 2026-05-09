# TEST-ARCH-002 Golden backend event sequence tests

Status: Planning
Sprint: Sprint 3.5
Type: Contract / Integration Test
Owner: Backend Events
Priority: P0

## Problem

We need golden event sequence tests that prove backend lifecycle order as one system, not only helper-level envelope tests.

## Source / architecture rule

Backend emits typed lifecycle events in a valid order. Frontend must render backend truth and not infer lifecycle locally.

## Scope

Create cheap golden sequence tests for:

1. deterministic click flow
2. deterministic assertion flow if feasible
3. LLM-required ambiguous planning flow using fake/stub LLM
4. runtime rejection flow

Expected deterministic sequence should include or explicitly account for:

- session_state
- run_started or documented checkpoint equivalent
- plan_ready
- confirmed
- execution_started or documented checkpoint equivalent
- step_recorded
- code_update
- run_completed

## Out of scope

- paid LLM
- real browser E2E
- frontend UI testing
- changing event semantics without explicit decision

## Required tests

- deterministic click emits expected event order
- no execution before confirmation
- step_recorded precedes code_update
- code_update precedes or accompanies run_completed according to contract
- rejection sequence is explicit

## Acceptance criteria

- golden sequence tests exist
- sequence failures are easy to diagnose
- tests run cheaply
- current deterministic fast path is covered

## Cost-aware verification plan

No tests/e2e.
No paid LLM.
Use fake browser/fake LLM.
