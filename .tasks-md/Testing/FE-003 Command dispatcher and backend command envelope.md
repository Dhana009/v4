# FE-003 Command dispatcher and backend command envelope

**Type:** Story  
**Status:** Testing  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Pending-command metadata and typed command contracts verified; frontend dispatcher contract green  
**Dependencies:** FE-001, EVENT-002, EVENT-003, BE-003  
**Blocks:** FE-004, FE-005, FE-008, replay controls  
**Version:** MR-4G v1  

---

## Product contribution

This story ensures every user action from UI becomes a typed backend command, not a direct state mutation.

## Architecture decision

Fixed:

- all UI commands use EVENT-002 envelope
- command_id/correlation id included
- UI does not optimistically mutate runtime truth
- typed rejections are renderable

## Command dispatcher contract

| Command | UI sources |
|---|---|
| llm_run/run_steps | prompt/input form |
| confirmed | plan review confirm |
| correction | plan review correction |
| option_selected | clarification/recovery |
| skip_step | recovery |
| stop_run | global control |
| replay_step/operation/all | replay controls |
| update_locator | picker/recovery locator UI |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE003-U-001 | Unit | confirm click | confirmed command envelope |
| FE003-U-002 | Unit | correction submit | correction command |
| FE003-U-003 | Unit | stop run | stop_run command |
| FE003-U-004 | Unit | command rejected | rejection rendered |
| FE003-I-001 | Integration | command through websocket | backend receives canonical shape |

## MR-4G test-only subtasks

- [ ] map FE-003 source rows
- [ ] inventory existing backend command/event contract tests
- [ ] define frontend command dispatcher expectations
- [ ] define typed command-envelope context fields for confirm / correction / clarification / recovery
- [ ] negative cases: stale / duplicate / missing command context
- [ ] boundary cases: rejected command, unknown command, disconnected submission
- [ ] test-only slice
- [ ] narrow implementation slice only after tests exist
- [ ] verification commands

## MR-4G scope note

- FE-003 is the command-dispatch side of the typed frontend envelope contract.
- The supported typed commands should stay aligned with the backend normalizer and preserve legacy fallback paths for other actions until their backend support exists.

## MR-4G implementation evidence

- `buildFrontendCommandEnvelope` now emits canonical typed command envelopes in `frontend/src/main.jsx`
- confirm / correction / clarification / recovery handlers now send typed envelopes with `command_id` and `schema_version`
- plan context fields such as `plan_id`, `plan_version`, and `step_id` are forwarded when available
- `runtime_rejected` backend events now preserve rejection reason and current state for rendering
- `python -m py_compile tests/test_frontend_event_command_contract.py` passed
- `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` returned `72 passed`
- `cd frontend && npm run build` succeeded
- no browser-startup E2E tests were run for this slice
- no backend/runtime/LLM/DOM changes

## MR-4H command-purity hardening

- read-model purity tests added alongside the command envelope contract coverage
- confirm, correction, clarification, and recovery handlers no longer optimistically mutate lifecycle truth in `frontend/src/main.jsx`
- typed command envelopes and backend command contract shapes remain unchanged
- backend `runtime_rejected` stays the rejection-reporting path and does not infer lifecycle success
- `python -m py_compile tests/test_frontend_event_command_contract.py` passed
- `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` returned `78 passed`
- `cd frontend && npm run build` succeeded
- remaining known gap: the frontend has no separate pending-command banner; it relies on backend events and the debug/error surface
- no backend/runtime/LLM/DOM changes

## MR-4I pending-command metadata hardening

- pending-command metadata tests added alongside the command envelope coverage
- typed command handlers now record pending command metadata without changing lifecycle truth
- pending metadata includes `command_id`, `command_type`, `created_at`, `created_sequence`, and `status`
- backend lifecycle events can acknowledge the pending metadata and `runtime_rejected` marks the matching command rejected
- typed command envelope shapes remain unchanged
- `python -m py_compile tests/test_frontend_event_command_contract.py` passed
- `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` returned `84 passed`
- `cd frontend && npm run build` succeeded
- remaining known gap: pending command metadata is tracked in runtime state but not surfaced as a dedicated panel card yet
- no backend/runtime/LLM/DOM changes

## Testing evidence

- implementation commit: `95afc7d` (`feat: track frontend pending command state`)
- prior command-purity commit: `35c26d2` (`feat: harden frontend command lifecycle purity`)
- latest focused result: `python -m pytest tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` returned `84 passed`
- build result: `cd frontend && npm run build` succeeded
- remaining known gap: pending-command metadata is tracked in runtime state but not surfaced as a dedicated panel card yet
- no backend/runtime/LLM/DOM changes

## Edge cases

- double click confirm
- command while disconnected
- stale plan in UI
- command rejected after optimistic spinner

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

First Codex task for FE-003 should be read-only:

```text
Read FE-003, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
