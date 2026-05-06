# FE-006 Recorded steps and code panel rendering

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** FE-002, EVENT-006, BE-009  
**Blocks:** recorded/code UI, E2E recording assertions  
**Version:** Batch 06 v1  

---

## Product contribution

This story renders backend-owned recorded steps and generated Playwright code.

## Architecture decision

Fixed:

- recorded steps come only from `step_recorded`
- code comes only from `code_update`
- UI preserves parent/child order from backend
- expected_outcome metadata is displayed as metadata only

## Rendering contract

| Panel | Data source |
|---|---|
| Recorded steps | step_recorded.recorded_step |
| Child operations | recorded_step.children |
| Code | code_update.lines |
| Diagnostics | code_update.diagnostics |
| Metadata | expected_outcome_metadata |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE006-U-001 | Unit | step_recorded event | recorded row appears |
| FE006-U-002 | Unit | children order | order preserved |
| FE006-U-003 | Unit | code_update | code panel updates |
| FE006-U-004 | Unit | diagnostic_only | diagnostics shown |
| FE006-I-001 | Integration | recording→code | panels match backend events |

## Edge cases

- duplicate recorded step
- code_update before recording
- failed recording
- long code output

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

First Codex task for FE-006 should be read-only:

```text
Read FE-006, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
