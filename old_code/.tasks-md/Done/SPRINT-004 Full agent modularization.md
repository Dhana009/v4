# SPRINT-004 Full agent modularization

Status: Done
Sprint: Sprint 4
Owner: Runtime Architecture
Source docs:
- SPRINT-003.5 Refactor readiness closure report
- REF-AUDIT-001 Agent Modularization Map
- REF-AUDIT-002 Characterization tests before extraction
- REF-001 through REF-004 review gates

## Problem / goal

`agent.py` remains too large and still mixes orchestration, execution, tool handlers, replay, snapshot, planning, and runtime helper responsibilities. The goal of Sprint 4 is to continue modularizing `agent.py` without changing backend truth semantics.

## Scope

- Behavior-preserving module extraction
- Strong regression validation after each coherent slice
- Documentation of blocked high-risk areas

## Out of scope

- Frontend redesign
- E2E harness refactor
- Silent behavior changes
- Test weakening

## Required tests

- broad non-E2E regression
- focused contract suites per extracted area

## Acceptance criteria

- `agent.py` is materially smaller
- module ownership is clearer
- broad non-E2E regression passes
- blocked high-risk areas are documented explicitly

## Evidence

- pending

## Verification commands/results

- pending
