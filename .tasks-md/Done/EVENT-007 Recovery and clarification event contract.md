# EVENT-007 Recovery and clarification event contract

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-002 Typed Event Contract  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** EVENT-001, EVENT-002, EVENT-003, BE-008  
**Blocks:** DEV-3 clarification/recovery UI, DEV-4 recovery E2E  
**Version:** Batch 03 v1  

---

## Product contribution

This story defines how backend asks the user for missing info or recovery decisions without guessing.

## Architecture decision

Fixed:

- clarification and recovery are backend-owned states
- frontend renders backend questions/options
- option_selected is validated command
- unresolved recovery blocks completion

## Event contracts

| Event | Required payload |
|---|---|
| clarification_needed | run_id, clarification_id, question, options?, reason |
| recovery_needed | run_id, recovery_id, step_id, operation_id?, failure_code, error_summary, options[] |
| step_failed | run_id, step_id, operation_id?, reason/evidence |

## Command contract

| Command | Required payload |
|---|---|
| option_selected | run_id, target_id, value |
| skip_step | run_id, step_id, reason |
| stop_run | run_id, reason? |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT007-C-001 | Contract | clarification event | accepted |
| EVT007-C-002 | Contract | recovery without failure_code | rejected |
| EVT007-U-001 | Unit | option_selected invalid id | rejected |
| EVT007-I-001 | Integration | failure → recovery_needed | emitted and renderable |

## Edge cases

- user answers wrong clarification
- recovery option stale
- skip without reason
- LLM claims recovery resolved

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

First Codex task for EVENT-007 should be read-only:

```text
Read EVENT-007, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
