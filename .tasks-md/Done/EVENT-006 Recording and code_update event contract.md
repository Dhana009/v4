# EVENT-006 Recording and code_update event contract

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-002 Typed Event Contract  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** EVENT-001, EVENT-003, BE-009, BE-010  
**Blocks:** DEV-3 Recorded/Code tabs, DEV-4 recording assertions, codegen integration  
**Version:** Batch 03 v1  

---

## Product contribution

This story defines how completed execution becomes visible recorded evidence and code update events.

## Architecture decision

Fixed:

- `step_recorded` is backend-owned
- recorded payload preserves parent/child operations
- `code_update` is triggered from recorded children, not LLM text

## Event contracts

| Event | Required payload |
|---|---|
| step_recorded | run_id, recorded_step, source_step_id, children[], evidence_refs |
| code_update | run_id, step_id?, lines[], diagnostics[], source_recording_ids |
| recording_failed if introduced | run_id, step_id, reason |

## Recorded child minimum

| Field | Required |
|---|---|
| operation_id | Yes |
| type/subtype | Yes |
| locator/value | Conditional |
| result | Yes |
| evidence_ref | Yes |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT006-C-001 | Contract | valid step_recorded parent/children | accepted |
| EVT006-C-002 | Contract | missing child evidence | rejected |
| EVT006-C-003 | Contract | code_update without lines | rejected or diagnostic-only by policy |
| EVT006-I-001 | Integration | recording emits code_update | both events captured |

## Edge cases

- child order differs from contract
- duplicate operation ids
- expected_outcome leaks into assertion target
- code_update emitted before recording finalized

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

First Codex task for EVENT-006 should be read-only:

```text
Read EVENT-006, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
