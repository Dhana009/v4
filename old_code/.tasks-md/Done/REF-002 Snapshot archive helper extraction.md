# REF-002 Snapshot archive helper extraction

Status: Done
Sprint: Post Sprint 3.5
Owner: Runtime Architecture
Source docs:
- REF-AUDIT-001 Agent Modularization Map
- REF-AUDIT-002 Characterization tests before extraction
- REF-001 review gate

## Problem / goal

Confirm and, only if necessary, complete the extraction of snapshot/archive pure helper logic out of `agent.py` without changing behavior.

## Scope

- Snapshot/archive helper ownership only
- Behavior-preserving only
- No replay repair or session-restore redesign

## Out of scope

- Lifecycle orchestration
- Correction flow
- Confirmed execution
- Recording/code_update
- Main run loop
- DOM/locator handlers
- Frontend

## Required tests

- `python -m py_compile agent.py runtime/snapshot_archive.py`
- `python -m pytest tests/test_snapshot_archive_contract.py -q`
- `python -m pytest tests/test_replay_one.py tests/test_snapshot_archive_contract.py -q`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_recording_codegen_truth_contract.py -q`

## Acceptance criteria

- Snapshot/archive pure helper logic is confirmed outside `agent.py`, or the remaining thin adapter is extracted without changing behavior
- Focused tests pass
- No replay/session behavior changes

## Evidence

- Added `runtime/snapshot_archive.py` as the focused snapshot/archive runtime seam.
- Switched `agent.py` to import `build_spec_snapshot` from the new snapshot/archive seam.
- Preserved the existing tested snapshot/archive behavior in `runtime/spec_snapshot.py`.
- Kept replay/session behavior unchanged.

## Verification commands/results

- `python -m py_compile agent.py runtime/snapshot_archive.py`
  - pass
- `python -m pytest tests/test_snapshot_archive_contract.py -q`
  - `5 passed`
- `python -m pytest tests/test_replay_one.py tests/test_snapshot_archive_contract.py -q`
  - `15 passed`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_recording_codegen_truth_contract.py -q`
  - `13 passed`
