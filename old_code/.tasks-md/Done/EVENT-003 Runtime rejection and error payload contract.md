# EVENT-003 Runtime rejection and error payload contract

Status: Done  
Sprint: Sprint 0  


**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-002 Typed Event Contract  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** EVENT-001, EVENT-002, BE-002, BE-003  
**Blocks:** all invalid transition/command paths, DEV-3 error UI, DEV-4 negative assertions  
**Version:** Batch 03 v1  

---

## Product contribution

This story makes failures and blocked actions explainable. Runtime rejections become typed payloads that frontend can render and E2E can assert.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| PLAN-002 | standard rejected-transition payload | define canonical rejection/error shape |
| BE-003 | rejected commands preserve backend state | command errors use this contract |
| BE-001 | invalid transitions fail closed | transition errors use this contract |

## Architecture decision

Fixed:

- rejection payload includes deterministic `rejection_code`
- current state and attempted transition are included where available
- no free-form-only error strings
- rejection does not mutate runtime truth except trace/evidence

## Payload contract

| Field | Required | Meaning |
|---|---|---|
| type | Yes | `runtime_rejected` or error family |
| run_id | Conditional | run scope |
| command_id | Optional | rejected command |
| rejection_code | Yes | deterministic reason |
| severity | Yes | info/warning/error/blocker |
| message | Yes | human-readable |
| current_state | Yes where available | run/plan/step/op status |
| attempted_transition | Optional | blocked transition/command |
| required_next_action | Optional | user/system unblock path |
| recoverable | Yes | can continue |
| evidence_ref | Optional | trace/artifact |

## Required rejection codes baseline

```text
UNKNOWN_COMMAND
MALFORMED_COMMAND
STALE_PLAN_VERSION
CONFIRMATION_REQUIRED
CLARIFICATION_REQUIRED
RECOVERY_OPEN
EXECUTION_IN_PROGRESS
UNKNOWN_STEP
UNKNOWN_OPERATION
MISSING_REASON
UNSUPPORTED_CAPABILITY
PRECONDITION_FAILED
```

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT003-C-001 | Contract | valid runtime_rejected | accepted |
| EVT003-C-002 | Contract | missing rejection_code | rejected |
| EVT003-U-001 | Unit | stale confirm | STALE_PLAN_VERSION |
| EVT003-U-002 | Unit | execute before confirm | CONFIRMATION_REQUIRED |
| EVT003-I-001 | Integration | frontend receives rejection | renderable payload |

## Edge cases

- multiple rejection causes
- recovery-open plus stale command
- unsupported capability inside confirmed plan
- rejected command after stop_run

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

First Codex task for EVENT-003 should be read-only:

```text
Read EVENT-003, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
