# TEST-ARCH-001 Backend contract confidence inventory

Status: Planning
Sprint: Sprint 3.5
Type: Test Architecture
Owner: Backend Contracts
Priority: P0

## Problem

The project has many unit and contract tests, but backend contract confidence is spread across many files. We need a clear matrix showing what is covered, what is missing, and what must be tested before refactor or feature expansion.

## Source / architecture rule

Backend owns runtime truth, typed events, command validation, confirmation, execution, recording, and completion state.

## Scope

Create/update a backend contract confidence inventory covering:

- session_state
- run_started
- plan_ready
- confirmed
- execution_started
- step_recorded
- code_update
- run_completed
- runtime_rejected
- recovery_needed
- correction flow
- stale command rejection
- late command rejection
- snapshot/archive safety
- deterministic fast path
- LLM-required path

## Out of scope

- implementation changes
- broad refactor
- paid E2E

## Required output

A matrix in .tasks-md showing:

| Contract | Existing test files | What is proven | Missing coverage | Priority | Recommended next test |

## Acceptance criteria

- all backend contracts are mapped
- missing coverage is explicit
- high-priority gaps are identified
- no code changes required

## Cost-aware verification plan

No E2E.
No paid LLM.
Read-only inspection and task-board update only.
