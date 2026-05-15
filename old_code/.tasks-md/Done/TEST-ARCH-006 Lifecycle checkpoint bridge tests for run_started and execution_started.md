# TEST-ARCH-006 Lifecycle checkpoint bridge tests for run_started and execution_started

Status: Done
Sprint: Sprint 3.5
Type: Contract Clarification
Owner: Backend Lifecycle
Priority: P0
Started: 2026-05-09

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

## Decision

- `run_started` contract:
  - mapped backend lifecycle checkpoint
  - currently represented by `PhaseTracker.set_phase("planning", reason="run_started")`
  - not a first-class typed backend event envelope today
- `execution_started` contract:
  - mapped backend lifecycle checkpoint
  - currently represented by confirmation acceptance returning `phase="executing"` plus `PhaseTracker.set_phase("executing", reason="confirmed", step_id=...)`
  - not a first-class typed backend event envelope today

## Evidence

- tests added:
  - `tests/test_lifecycle_checkpoint_contract.py`
- commands run:
  - `python -m py_compile runtime/event_contracts.py tests/test_lifecycle_checkpoint_contract.py`
  - `python -m pytest tests/test_lifecycle_checkpoint_contract.py -q`
  - `python -m pytest tests/test_backend_event_sequences.py tests/test_event_sequence_contract.py tests/test_event_contract.py tests/test_event_contracts.py -q`
- results:
  - compile passed
  - lifecycle checkpoint suite: `4 passed`
  - backend sequence / contract suites: `27 passed`

## Known follow-up

- Typed `run_started` / `execution_started` backend events are not currently required for Sprint 3.5 because the mapped checkpoint contract is now explicit and tested.
- If the product later needs these as first-class frontend-rendered lifecycle events, that should be a deliberate product/protocol change rather than a silent test-driven promotion.
