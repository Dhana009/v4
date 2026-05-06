# EVENT-001 Canonical backend event envelope

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-002 Typed Event Contract  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** BE-001, BE-002, EPIC-002  
**Blocks:** EVENT-003, EVENT-004 to EVENT-009, DEV-3 event store, DEV-4 event capture  
**Version:** Batch 03 v1  

---

## Product contribution

This story defines the shared backend event envelope all event families use. It lets frontend and E2E read events consistently without per-event guessing.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| SOURCE-001 | lifecycle changes must become typed backend events | define event envelope |
| BE-002 | backend event emitter validates type and identifiers | envelope validation |
| Frontend/UI Spec | frontend renders backend truth | payload must be renderable |
| E2E Strategy | harness captures event/log evidence | payload must be assertion-friendly |

## Architecture decision

Fixed:

- every backend event has `type`, `run_id` where run-scoped, `emitted_at`, and schema version
- step/operation events include identity
- event payload is data, not prose-only explanation
- event envelope is separate from event-specific body

## Event envelope contract

| Field | Required | Meaning |
|---|---|---|
| type | Yes | canonical event name |
| schema_version | Yes | event contract version |
| run_id | Conditional | required for run-scoped events |
| plan_id | Conditional | plan-scoped events |
| plan_version | Conditional | stale version protection |
| step_id | Conditional | step-scoped events |
| operation_id | Conditional | operation-scoped events |
| emitted_at | Yes | backend timestamp |
| source | Yes | backend subsystem |
| status | Optional | lifecycle/status |
| payload | Yes | event-specific body |
| trace_id/evidence_ref | Optional | diagnostics |

## Direct vs indirect dependencies

Direct blockers: EVENT-003 to EVENT-009.  
Indirect consumers: DEV-3 event store, DEV-4 event capture, trace UI.

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT001-C-001 | Contract | valid run-scoped event | accepted |
| EVT001-C-002 | Contract | missing type | rejected |
| EVT001-C-003 | Contract | unknown type | rejected |
| EVT001-C-004 | Contract | step event missing step_id | rejected |
| EVT001-C-005 | Contract | operation event missing operation_id | rejected |
| EVT001-I-001 | Integration | event passes backend bridge | frontend receives same envelope |

## Edge cases

- duplicate terminal event
- event emitted after stopped run
- event has stale plan_version
- payload only contains prose
- legacy event without schema_version

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current event/command files and WebSocket bridge locations
- current backend-to-frontend payload names
- current frontend consumers
- current test coverage
- compatibility risks with existing event names
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- event/command ownership is unclear
- current code conflicts with source and migration path is unclear
- payload shape would force frontend to infer runtime truth
- LLM would own a truth event
- schema/test coverage cannot be written first
- implementation requires broad backend/frontend rewrite
- compatibility adapter decision is unclear

---

## Codex execution summary

First Codex task for EVENT-001 should be read-only:

```text
Read EVENT-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
