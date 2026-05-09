# REF-AUDIT-002 Characterization tests before extraction

Status: Planning
Sprint: Sprint 3.5
Type: Refactor Readiness
Owner: Runtime Architecture
Priority: P1

## Problem

agent.py should be modularized, but extraction is risky unless behavior is characterized first.

## Source / architecture rule

Refactor must preserve backend truth, event contracts, confirmation gate, recording/code_update, LLM policy, and replay behavior.

## Scope

Define and add characterization tests required before any extraction.

Areas:

- plan_ready builder behavior
- correction state behavior
- confirmed execution validation
- recording/code_update payloads
- deterministic fast path
- DOM/locator handlers
- replay/snapshot helpers

## Out of scope

- extracting modules
- rewriting agent.py
- formatting-only refactor

## Required tests

At minimum, identify or add characterization tests for first safe extraction candidate.

## Acceptance criteria

- first extraction candidate is identified
- required tests are green
- risky extractions are explicitly blocked
- no production behavior changed

## Cost-aware verification plan

Focused non-E2E tests only.
