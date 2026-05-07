# EVENT-009 Capability gap event contract

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-002 Typed Event Contract  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** EVENT-001, EVENT-003, BE-011  
**Blocks:** Trace UI, advanced capability backlog, DEV-4 unsupported-flow tests  
**Version:** Batch 03 v1  

---

## Product contribution

This story defines how unsupported capabilities become typed, traceable gaps instead of hidden failures.

## Architecture decision

Fixed:

- gap is backend-owned event
- unsupported capability does not pretend success
- LLM may explain gap but cannot claim support

## Event contract

| Field | Required | Meaning |
|---|---|---|
| gap_id | Yes | unique gap |
| needed_capability | Yes | upload/download/popup/iframe/etc. |
| run_id/step_id/operation_id | Optional | source context |
| current_support | Yes | unsupported/partial |
| user_impact | Yes | what cannot complete |
| recommended_followup | Optional | backlog hint |
| evidence_ref | Optional | artifact |
| status | Yes | recorded/open/closed |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT009-C-001 | Contract | valid gap | accepted |
| EVT009-C-002 | Contract | missing capability | rejected |
| EVT009-I-001 | Integration | unsupported op | capability_gap_recorded |

## Edge cases

- repeated same gap
- partial support
- gap discovered during confirmed execution
- user chooses to continue

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

First Codex task for EVENT-009 should be read-only:

```text
Read EVENT-009, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
