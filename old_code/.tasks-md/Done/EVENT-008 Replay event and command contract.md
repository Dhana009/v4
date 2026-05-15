# EVENT-008 Replay event and command contract

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
**Dependencies:** EVENT-001, EVENT-002, EVENT-003, BE-012  
**Blocks:** DEV-3 replay controls, DEV-4 replay smoke, P1 replay repair  
**Version:** Batch 03 v1  

---

## Product contribution

This story defines backend-owned replay commands and events so replay is not frontend simulation.

## Architecture decision

Fixed:

- replay has separate command/event path
- precondition result is explicit
- replay_step, replay_operation, replay_all are distinct modes
- robust repair is out of P0 scope

## Command contracts

| Command | Required payload |
|---|---|
| replay_step | run_id?, recorded_step_id |
| replay_operation | recorded_step_id, operation_id |
| replay_all | recorded_run_id/session_id, stop_on_error? |

## Event contracts

| Event | Required payload |
|---|---|
| replay_started | replay_run_id, target, mode |
| replay_result | replay_run_id, status, precondition_status, evidence_ref?, error? |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT008-C-001 | Contract | replay_step command | accepted |
| EVT008-C-002 | Contract | replay_operation missing parent | rejected |
| EVT008-C-003 | Contract | replay_result with precondition failure | accepted |
| EVT008-I-001 | Integration | replay while execution active | rejected or isolated by policy |

## Edge cases

- recorded target missing
- wrong page precondition
- replay_all partial failure
- user stops replay

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

First Codex task for EVENT-008 should be read-only:

```text
Read EVENT-008, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
