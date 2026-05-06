# FE-009 Frontend test hooks and accessibility contract

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** FE-001, FE-002, FE-003, PLAN-005  
**Blocks:** DEV-4 E2E UI tests, accessibility-safe UI  
**Version:** Batch 06 v1  

---

## Product contribution

This story makes the frontend testable and accessible.

## Architecture decision

Fixed:

- stable data-testid/test hooks for P0 UI surfaces
- accessible roles/names for buttons/forms/dialogs
- E2E should not rely on brittle CSS
- test hooks do not conflict with target page automation

## Required hooks

| UI area | Hook/accessibility |
|---|---|
| root host | stable root id/testid |
| prompt input | role/textbox + label |
| run button | role/button name |
| plan review | plan panel/testid |
| confirm/correction | role buttons/inputs |
| recovery/clarification | dialog/card hooks |
| recorded/code | panels and rows |
| trace | panel/log rows |
| picker | candidate rows and actions |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE009-U-001 | Unit | root has hook | stable |
| FE009-U-002 | Unit | buttons accessible | roles/names |
| FE009-U-003 | Unit | panels testable | hooks exist |
| FE009-E-001 | E2E | locate plan panel | stable selector |
| FE009-E-002 | E2E | locate recovery option | stable selector |

## Edge cases

- duplicate labels
- hidden panels
- responsive layout
- host isolation

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

First Codex task for FE-009 should be read-only:

```text
Read FE-009, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
