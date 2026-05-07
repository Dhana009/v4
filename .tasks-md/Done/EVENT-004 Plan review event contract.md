# EVENT-004 Plan review event contract

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-002 Typed Event Contract  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** EVENT-001, EVENT-002, EVENT-003, BE-004, BE-005  
**Blocks:** DEV-3 plan review UI, DEV-4 plan/correction E2E  
**Version:** Batch 03 v1  

---

## Product contribution

This story defines the event/command contract for plan review, correction, and confirmation.

## Architecture decision

Fixed:

- `plan_ready` comes from backend active plan only
- plan review events include plan_id/version and ordered steps
- confirm/correction commands reference current plan/version

## Plan event contract

| Event | Required payload |
|---|---|
| plan_ready | run_id, plan_id, plan_version, status, steps[], summary |
| plan_cancelled/rejected if introduced | run_id, plan_id, reason |
| plan_corrected if introduced | old/new version, correction summary |

## Plan command contract

| Command | Required payload |
|---|---|
| confirmed | run_id, plan_id, plan_version |
| correction | run_id, plan_id, plan_version, message or diff |
| option_selected | clarification/recovery id + value |

## Step preview payload

| Field | Required |
|---|---|
| step_id | Yes |
| intent | Yes |
| expected_outcome_metadata | Optional |
| children[] | Yes |
| precondition/postcondition | Optional |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT004-C-001 | Contract | plan_ready full payload | accepted |
| EVT004-C-002 | Contract | plan_ready missing plan_version | rejected |
| EVT004-C-003 | Contract | confirmed stale version | rejection |
| EVT004-I-001 | Integration | correction creates new plan_ready | old version not confirmable |

## Edge cases

- duplicate plan_ready
- correction while execution active
- confirm while clarification open
- plan preview has duplicate step_id

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

First Codex task for EVENT-004 should be read-only:

```text
Read EVENT-004, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
