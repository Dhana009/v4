# FE-002 Frontend typed event store

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Frontend event-store and command-dispatch contracts verified and complete  
**Dependencies:** FE-001, EVENT-001, EVENT-003  
**Blocks:** FE-004, FE-005, FE-006, FE-007, DEV-4 UI assertions  
**Version:** MR-4F v1  

---

## Product contribution

This story creates the frontend state store that mirrors backend events without becoming runtime truth.

## Architecture decision

Fixed:

- frontend store is read-model only
- backend events are canonical input
- unknown/malformed events are rejected/logged
- terminal state comes only from backend event

## MR-4F test-only subtasks

- [x] map FE-002 / FE-003 source rows
- [x] inventory existing command/event tests
- [x] define frontend event-store/read-model shell expectations
- [x] define frontend command dispatcher shell expectations
- [x] add test-only slice
- [x] verification commands
- [x] stop before implementation unless tests exist and fail/xfail narrowly
- [x] implementation MR scope after tests

## MR-4F scope note

- Historical note: FE-002 and FE-003 were delivered together as the frontend event-store / command-dispatch pair.

## MR-4F test-only slice evidence

- `tests/test_frontend_event_command_contract.py` added
- `python -m py_compile tests/test_frontend_event_command_contract.py` passed
- `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py -q` returned `64 passed, 2 xfailed`
- dedicated event-store shell helper and typed command-envelope metadata remain planned
- no frontend/runtime/backend changes

## MR-4G event-store test-only slice

- [x] map FE-002 source rows
- [x] inventory existing backend command/event contract tests
- [x] define frontend event read-model expectations
- [x] define frontend no-inference expectations for completed / recorded / recovery state
- [x] negative cases: out-of-order backend events, unknown events, stale / duplicate terminal events
- [x] boundary cases: rejected commands do not mutate the event store
- [x] test-only slice
- [x] narrow implementation slice only after tests exist
- [x] verification commands

## MR-4G scope note

- FE-002 stays the read-model side of the typed event store shell.
- FE-003 covers the command-dispatch side of the typed frontend envelope contract.
- The next implementation step should remain small: event-store alias plus typed envelope helper, not a broad UI rewrite.

## MR-4G implementation evidence

- `useFrontendEventStore` now aliases the transport shell in `frontend/src/main.jsx`
- `runtime_rejected` backend events now surface rejection reason and current state without mutating lifecycle truth
- `python -m py_compile tests/test_frontend_event_command_contract.py` passed
- `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` returned `72 passed`
- `cd frontend && npm run build` succeeded
- no browser-startup E2E tests were run for this slice
- no backend/runtime/LLM/DOM changes

## MR-4H read-model purity hardening

- read-model purity tests added in `tests/test_frontend_event_command_contract.py`
- optimistic lifecycle mutation removed from confirm, correction, clarification, and recovery command handlers in `frontend/src/main.jsx`
- backend events remain the only lifecycle/read-model transition source
- `python -m py_compile tests/test_frontend_event_command_contract.py` passed
- `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` returned `78 passed`
- `cd frontend && npm run build` succeeded
- remaining known gap: the frontend reports rejected commands through `lastError` and timeline only; no separate pending-command banner is surfaced in the panel
- no backend/runtime/LLM/DOM changes

## MR-4I pending-command metadata hardening

- pending-command metadata tests added in `tests/test_frontend_event_command_contract.py`
- `frontend/src/main.jsx` now tracks non-lifecycle pending command metadata separately from `runState` / `interactionMode`
- command send handlers record `command_id`, `command_type`, `created_at`, `created_sequence`, and `status`
- backend lifecycle events may acknowledge pending metadata, and `runtime_rejected` marks matching pending commands as rejected without lifecycle mutation
- `python -m py_compile tests/test_frontend_event_command_contract.py` passed
- `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` returned `84 passed`
- `cd frontend && npm run build` succeeded
- remaining known gap: pending command metadata is stored in the frontend runtime state but not yet surfaced as a dedicated visible panel card
- no backend/runtime/LLM/DOM changes

## Done evidence

- implementation commit: `95afc7d` (`feat: track frontend pending command state`)
- prior purity commit: `35c26d2` (`feat: harden frontend command lifecycle purity`)
- latest focused result: `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` returned `84 passed`
- build result: `cd frontend && npm run build` succeeded
- remaining pending-command banner is future UX polish, not part of FE-002 acceptance
- no backend/runtime/LLM/DOM changes

## Store state slices

| Slice | Source event families |
|---|---|
| session | ready/session_state |
| run | run_started/run_completed/runtime_rejected |
| plan | plan_ready |
| execution | step_validating/step_executing/step_failed |
| recovery | clarification_needed/recovery_needed |
| recording | step_recorded/code_update |
| replay | replay_started/replay_result |
| gaps | capability_gap_recorded |
| trace | diagnostic/evidence refs |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE002-U-001 | Unit | plan_ready event | plan slice updated |
| FE002-U-002 | Unit | run_completed event | terminal state rendered |
| FE002-U-003 | Unit | malformed event | rejected/logged |
| FE002-U-004 | Unit | LLM prose message | no lifecycle mutation |
| FE002-I-001 | Integration | event stream sequence | store matches backend sequence |

## Edge cases

- out-of-order event
- duplicate terminal event
- stale plan_version
- event for unknown run_id

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current frontend entry points and overlay injection path
- current Shadow DOM host/components if any
- current WebSocket/event consumer code
- current command sending code
- current plan/recorded/code/trace UI state ownership
- current picker/element-info UI behavior
- current tests and frontend test hooks
- current legacy overlay dependencies
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- frontend would infer lifecycle truth locally
- implementation targets legacy overlay as the new product architecture
- event/command contracts are missing or incompatible
- backend truth fields are not enough to render safely
- UI command would mutate runtime state directly
- current code requires broad rewrite before tests
- frontend test hooks cannot be defined
- Shadow DOM isolation conflicts with product page behavior

---

## Codex execution summary

First Codex task for FE-002 should be read-only:

```text
Read FE-002, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
