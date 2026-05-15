# DEV-1 Backend Runtime and Recording - Done

Status: Done  
Sprint: Sprint 0  


Status: Done
Owner: DEV-1
Branch: `dev1/backend-isolation-contract-tests`
Main baseline for merged items: `908f4d0`
Current main audit snapshot: `9823c08`

This file records completed DEV-1 backend work.
Items are split by merge state so branch-only completions stay visible.

Current main status:
- DEV-1 backend runtime, event, recovery, snapshot, and recording/codegen truth work is merged on local main.
- Historical branch-only rows below are retained for provenance and later batch-merge context.

## Merged to local main

| Item | Commit | Files changed | Verification | Merge state |
|---|---|---|---|---|
| MR-1B backend/event contract tests | `f117599` | `tests/test_event_contract.py`, `tests/test_command_contract.py`, `tests/test_event_sequence_contract.py` | `9 passed, 16 xfailed` | merged to local main at `eb1bd31` |
| MR-1C typed backend event/command seam | `f7e3847` | `runtime/event_contracts.py`, `server.py`, `agent.py`, `tests/test_event_contract.py`, `tests/test_command_contract.py`, `tests/test_event_sequence_contract.py` | `41 passed, 2 xfailed` | merged to local main at `eb1bd31` |
| MR-1D stale confirmation/run-context guard | `176cad2` | `agent.py`, `tests/test_event_sequence_contract.py` | `42 passed, 1 xfailed` | merged to local main at `eb1bd31` |
| MR-1E session_state websocket handshake | `f7e1c61` | `runtime/event_contracts.py`, `server.py`, `agent.py`, `tests/test_event_contract.py` | `43 passed` focused backend/event; `11 passed` websocket/session | merged to local main at `908f4d0` |

## Done on DEV-1 branch, pending later batch merge to main

| Item | Commit | Files changed | Verification | Merge state |
|---|---|---|---|---|
| MR-1A backend/event mapping | branch task | planning mapping only | mapping review complete | branch-only, no production changes |
| Backend/event foundation established | branch sequence | DEV-1 backend/event plan and branch history | branch board maintained; later merged slices tracked separately | branch-only foundation state |
| Backend isolation recovery-state leak fix | `1b8c084` | `agent.py`, `tests/test_backend_isolation_contract.py` | `50 passed` | branch-only, pending later batch merge |
| Snapshot/archive contract tests | `112a481` | `tests/test_snapshot_archive_contract.py` | `34 passed, 2 xfailed` when introduced | branch-only, pending later batch merge |
| Late-event contract tests | `98944ad` | `tests/test_late_event_contract.py` | `35 passed, 6 xfailed` when introduced | branch-only, pending later batch merge |
| Stale backend command rejection | `cd438d7` | `agent.py`, `runtime/event_contracts.py`, `tests/test_late_event_contract.py` | `38 passed, 3 xfailed` when introduced | branch-only, pending later batch merge |
| Late confirmation rejection for completed runs | `6b03a82` | `agent.py`, `runtime/event_contracts.py`, `tests/test_late_event_contract.py` | `45 passed, 2 xfailed` after implementation batch | branch-only, pending later batch merge |
| Process-boundary contract tests | `2011da2` | `tests/test_process_boundary_contract.py` | `45 passed, 2 xfailed` when added | branch-only, pending later batch merge |
| Safe backend snapshot/archive loader seam | `ac1bcb5` | `runtime/spec_snapshot.py` | `47 passed` focused backend contract set | branch-only, pending later batch merge |
| Recording/codegen truth contract tests | `8932478` | `tests/test_recording_codegen_truth_contract.py` | `50 passed, 1 xfailed` focused backend contract set | branch-only, pending later batch merge |


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
