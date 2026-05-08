# EVENT-005 Step execution event contract

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
**Dependencies:** EVENT-001, EVENT-003, BE-005, BE-006  
**Blocks:** DEV-3 execution rendering, DEV-4 step execution assertions  
**Version:** Batch 03 v1  

---

## Product contribution

This story defines how backend reports operation validation/execution/failure while running the confirmed plan.

## Architecture decision

Fixed:

- execution events are operation-aware
- cursor identity is included
- frontend cannot infer active operation from prose

## Event contracts

| Event | Required payload |
|---|---|
| step_validating | run_id, plan_id/version, step_id, operation_id, target/context |
| step_executing | run_id, step_id, operation_id, type/subtype, locator_ref? |
| step_failed | run_id, step_id, operation_id?, error_summary, failure_code |
| step_skipped | run_id, step_id, reason |
| operation_succeeded if introduced | run_id, step_id, operation_id, evidence_ref |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT005-C-001 | Contract | step_executing with operation_id | accepted |
| EVT005-C-002 | Contract | operation event missing operation_id | rejected |
| EVT005-C-003 | Contract | failure missing error_summary | rejected |
| EVT005-I-001 | Integration | wrong operation blocked | runtime_rejected event |

## Edge cases

- same target in multiple steps
- operation failed after partial action
- navigation invalidates page context
- cursor mismatch

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

First Codex task for EVENT-005 should be read-only:

```text
Read EVENT-005, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
