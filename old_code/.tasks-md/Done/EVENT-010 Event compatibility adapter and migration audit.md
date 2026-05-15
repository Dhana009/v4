# EVENT-010 Event compatibility adapter and migration audit

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
**Blocks:** safe migration from current event names to canonical contract  
**Version:** Batch 03 v1  

---

## Product contribution

This story prevents breaking current behavior while migrating to canonical event/command contracts.

## Architecture decision

Fixed:

- inspect current event/command names before renaming
- define temporary adapter only when needed
- new work targets canonical names
- legacy overlay/event paths are transitional

## Migration audit requirements

| Area | Inspect |
|---|---|
| backend emitters | event names/payloads |
| websocket bridge | transport shape |
| frontend consumers | event handlers/store |
| tests | names assumed |
| legacy overlay | transitional dependencies |
| E2E/log capture | event parsing |

## Adapter decision table

| Current state | Decision |
|---|---|
| current name matches canonical | keep |
| current name differs but widely used | adapter + migration note |
| current payload lacks required fields | adapter enriches or story blocks |
| current frontend infers missing state | block until payload fixed |
| legacy overlay-only event | mark transitional, do not target new work |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT010-A-001 | Audit | list current events | complete map |
| EVT010-A-002 | Audit | list current commands | complete map |
| EVT010-C-001 | Contract | legacy name adapter | canonical output |
| EVT010-I-001 | Integration | frontend consumes canonical event | no inference |

## Edge cases

- same event name with different payloads
- hidden event emitted only in failure path
- frontend depends on text/prose
- tests assert old names

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

First Codex task for EVENT-010 should be read-only:

```text
Read EVENT-010, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
