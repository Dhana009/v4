# FE-002 Frontend typed event store

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** FE-001, EVENT-001, EVENT-003  
**Blocks:** FE-004, FE-005, FE-006, FE-007, DEV-4 UI assertions  
**Version:** Batch 06 v1  

---

## Product contribution

This story creates the frontend state store that mirrors backend events without becoming runtime truth.

## Architecture decision

Fixed:

- frontend store is read-model only
- backend events are canonical input
- unknown/malformed events are rejected/logged
- terminal state comes only from backend event

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
