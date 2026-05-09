# REF-AUDIT-001 agent.py modularization map

Status: Planning
Sprint: Sprint 3.5
Type: Refactor Readiness
Owner: Runtime Architecture
Priority: P0

## Problem

agent.py contains too many responsibilities. Refactoring it directly is risky unless each responsibility has tests first.

## Source / architecture rule

Refactor must preserve backend runtime truth, event contracts, command validation, confirmation, recording, and replay behavior.

## Scope

Create a modularization map for agent.py.

Map:

- lifecycle orchestration
- plan_ready construction
- plan correction flow
- confirmed execution
- deterministic fast path
- DOM/locator tools
- recording/code_update
- replay/snapshot
- LLM policy gateway calls
- telemetry
- recovery flow

For each area, document:

| Responsibility | Functions/classes | Existing tests | Missing characterization tests | Risk | Suggested module | Extraction order |

## Out of scope

- no code extraction
- no behavior change
- no formatting-only refactor

## Acceptance criteria

- agent.py responsibilities are mapped
- safest extraction candidates are identified
- risky extraction areas are blocked until tests exist
- no production code changed

## Cost-aware verification plan

No E2E.
No paid LLM.
Static inspection only.
