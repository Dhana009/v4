# FE-008 Picker and element candidate UI

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** FE-002, FE-003, DOM-002, DOM-005, DOM-009  
**Blocks:** locator/picker workflow, DOM E2E  
**Version:** Batch 06 v1  

---

## Product contribution

This story displays exact element and ancestor candidates so the user can choose correct target level when needed.

## Architecture decision

Fixed:

- picker UI displays candidates; backend validates final locator
- exact node is not automatically final target
- ancestor levels are visible
- update_locator command is typed and backend-validated

## Candidate UI contract

| Display item | Source |
|---|---|
| exact node | DOM-002 candidate |
| interactive ancestor | DOM-005 |
| card/row/form/dialog/section | DOM-005 |
| risk flags | DOM-002/DOM-003/DOM-004 |
| validation status | DOM-004 |
| update action | DOM-009 command |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE008-U-001 | Unit | nested span candidate | ancestor options shown |
| FE008-U-002 | Unit | duplicate CTA | risk/ambiguity shown |
| FE008-U-003 | Unit | select candidate | update_locator/selection command |
| FE008-U-004 | Unit | hidden candidate | warning shown |
| FE008-I-001 | Integration | picker target levels | UI displays levels |

## Edge cases

- long ancestor list
- identical candidate labels
- code block candidate
- stale validation result

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

First Codex task for FE-008 should be read-only:

```text
Read FE-008, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
