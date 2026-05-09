# TEST-ARCH-004 Recording code_update contract integration tests

Status: Planning
Sprint: Sprint 3.5
Type: Integration Test
Owner: Recording / Codegen
Priority: P1

## Problem

Recording/code_update are well covered at helper level, but we need one backend integration sequence proving step_recorded -> code_update -> run_completed from backend-owned evidence.

## Source / architecture rule

Recording and code_update must be backend-evidence-backed. LLM cannot invent successful recorded steps.

## Scope

Add cheap integration tests for:

- deterministic click recording
- deterministic assertion recording
- corrected multi-child plan recording if feasible
- failed/unresolved child does not produce code_update

## Out of scope

- paid LLM
- real browser E2E
- broad codegen redesign

## Required tests

- step_recorded emitted after successful execution evidence
- code_update emitted after step_recorded
- expected_outcome remains parent metadata
- failed child does not produce trusted generated line
- multi-child order is preserved

## Acceptance criteria

- recording/code_update path is integration-tested
- backend evidence requirement is enforced
- focused tests pass

## Cost-aware verification plan

No paid E2E.
Use fake execution evidence.
