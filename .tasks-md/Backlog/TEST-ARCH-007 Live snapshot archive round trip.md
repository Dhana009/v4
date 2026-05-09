# TEST-ARCH-007 Live snapshot archive round trip

Status: Backlog
Sprint: Sprint 3.5 Stretch
Type: Integration Test
Owner: Snapshot / Replay
Priority: P2

## Problem

Snapshot/archive safety is covered at unit level, but not as a live backend round-trip.

## Scope

Test:

- live run
- save snapshot
- reload snapshot
- preserve completed_step_ids
- preserve recorded_steps
- preserve expected_outcome / observed_outcome
- reject malformed archive safely

## Out of scope

- full replay repair
- frontend save/load UX
- paid E2E unless required

## Acceptance criteria

- live snapshot/archive round trip is tested cheaply
- replay preconditions remain safe
