# TEST-ARCH-005 Fast path vs LLM path integration contract tests

Status: Planning
Sprint: Sprint 3.5
Type: Integration / Policy Test
Owner: Backend Policy
Priority: P1

## Problem

Sprint 3 proved deterministic and LLM-required paths through E2E. We need cheaper integration tests proving both paths preserve backend truth without paid E2E.

## Source / architecture rule

Deterministic path should avoid LLM when safe. LLM path should trigger when intent is ambiguous/broad. Both must preserve backend confirmation, execution contract, recording, and telemetry.

## Scope

Add cheap integration tests comparing:

- deterministic picked click path
- deterministic picked assertion path
- ambiguous action path using fake/stub LLM
- broad planning fallback using fake/stub LLM if feasible

## Out of scope

- paid LLM
- real browser E2E
- frontend UI

## Required tests

- deterministic path uses no model call
- ambiguous path uses fake model call
- fast path does not trigger for ambiguous input
- both paths emit compatible plan_ready structures
- both paths require confirmation before execution

## Acceptance criteria

- fast path and LLM path are covered in one cheap suite
- backend truth is preserved
- telemetry/purpose behavior is asserted where possible

## Cost-aware verification plan

No paid E2E.
Use fake/stub model and fake browser.
