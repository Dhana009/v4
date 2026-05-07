# DEV-1 Planned Backend Contract Work

Status: Planning / Pending
Owner: DEV-1
Branch: `dev1/backend-isolation-contract-tests`

This file tracks picked-but-not-started DEV-1 backend slices.

## Replay smoke/basic replay contract hardening

Why picked:
- Replay smoke is the next backend-owned confidence step after recording/codegen truth.

Next test-first slice:
- Extend replay smoke coverage around page/precondition correctness and typed failure reporting.

Boundaries:
- Backend-only
- No replay repair
- No frontend
- No fixture expansion

## Backend restart/session-load integration beyond narrow snapshot/archive loader seam

Why picked:
- Snapshot loading exists now, but restart/session-load integration is not yet proven.

Next test-first slice:
- Add backend tests that describe restart/load safety without durable persistence.

Boundaries:
- Backend-only
- No full restore UX
- No persistence rewrite

## Load-session/reconnect integration beyond session_state shape

Why picked:
- session_state handshake is stable, but reconnect/load-session behavior beyond the initial handshake is not the current slice.

Next test-first slice:
- Add tests that describe reconnect/load invariants and isolate state after reconnect.

Boundaries:
- Keep current session_state contract
- No frontend inference
- No process-wide restore

## Broader backend save/load/replay evidence checks

Why picked:
- Recording/archive/replay evidence is backend-owned and needs more coverage before deeper replay work.

Next test-first slice:
- Add negative tests for evidence rejection, archive safety, and replay preconditions using backend-owned payloads only.

Boundaries:
- No replay repair
- No E2E harness
- No trace/export
