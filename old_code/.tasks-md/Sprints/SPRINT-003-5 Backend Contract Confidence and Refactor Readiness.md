# SPRINT-003.5 Backend Contract Confidence and Refactor Readiness

Status: Planning
Sprint: Sprint 3.5
Type: Stabilization / Test Architecture / Refactor Readiness
Priority: P0

## Goal

Create a cheap, reliable backend-system contract and integration safety net before starting the next product feature sprint or refactoring agent.py.

## Why this sprint exists

Sprint 3 proved:
- simple deterministic flows can run with 0 LLM calls
- ambiguous LLM-required flow still calls LLM correctly
- current E2E acceptance is green
- non-E2E regression passed

But the current codebase still has risk:
- agent.py owns too many responsibilities
- backend event sequence confidence is split across many helper-level tests
- no cheap live backend sequence harness exists
- paid E2E is too expensive to be the only confidence gate
- run_started and execution_started are not clearly first-class typed backend events or explicitly tested lifecycle checkpoints

## Source / architecture rules

- Backend owns runtime truth.
- Backend owns lifecycle state.
- Backend owns typed events and command validation.
- LLM proposes only.
- Frontend renders backend events only.
- Recording/code_update must be backend evidence-backed.
- Refactoring must not begin without characterization tests.

## Selected Sprint 3.5 work

1. TEST-ARCH-001 Backend contract confidence inventory
2. REF-AUDIT-001 agent.py modularization map
3. TEST-ARCH-003 WebSocket command-to-event integration harness
4. TEST-ARCH-002 Golden backend event sequence tests
5. TEST-ARCH-006 Lifecycle checkpoint bridge tests for run_started/execution_started
6. TEST-ARCH-004 Recording/code_update contract integration tests
7. TEST-ARCH-005 Fast path vs LLM path integration contract tests
8. REF-AUDIT-002 Characterization tests before extraction

Stretch:
- TEST-ARCH-007 Live snapshot/archive round-trip

## Success criteria

Sprint 3.5 is complete only when:

- backend contract coverage matrix is updated
- agent.py responsibility map exists
- cheap backend integration harness exists
- deterministic backend event sequence is tested without paid E2E
- LLM-path backend event sequence is tested with fake/stub LLM, not paid LLM
- confirmation gate is tested in integration
- recording/code_update sequence is tested in integration
- run_started/execution_started status is clarified and tested
- refactor extraction order is documented
- no agent.py extraction starts before characterization tests exist

## Non-goals

- no new product features
- no frontend redesign
- no broad replay repair
- no multi-model expansion
- no broad agent.py refactor
- no paid E2E unless explicitly approved
