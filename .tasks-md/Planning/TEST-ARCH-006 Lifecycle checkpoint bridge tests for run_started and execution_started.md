# TEST-ARCH-006 Lifecycle checkpoint bridge tests for run_started and execution_started

Status: Planning
Sprint: Sprint 3.5
Type: Contract Clarification
Owner: Backend Lifecycle
Priority: P0

## Problem

The audit found run_started and execution_started are lifecycle checkpoints in planning/testing docs, but in code they are still phase/log markers rather than clearly first-class typed backend events.

## Source / architecture rule

Lifecycle transitions must be observable and testable. Event-driven architecture requires clear backend-owned lifecycle truth.

## Scope

Clarify and test the status of:

- run_started
- execution_started

Decision options:

1. Promote them to typed backend events.
2. Keep them as explicit trace/checkpoint markers.
3. Map them to existing typed status/session events and document that mapping.

## Out of scope

- broad frontend changes
- changing UI rendering unless required later
- paid E2E

## Required tests

Depending on decision:

- if typed events: event envelope tests and sequence tests
- if checkpoints: trace/checkpoint tests proving stable markers
- if mapped: tests proving mapping from backend status/session state

## Acceptance criteria

- run_started and execution_started are no longer ambiguous
- task board documents chosen contract
- tests prove the chosen contract
- no frontend lifecycle inference is introduced

## Cost-aware verification plan

Focused backend tests only.
No paid E2E.
