# FE-010 Legacy overlay migration and compatibility audit

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** FE-001, EVENT-010, EPIC-005  
**Blocks:** safe migration, implementation sequencing  
**Version:** Batch 06 v1  

---

## Product contribution

This story prevents the new Shadow DOM frontend from being mixed with legacy overlay assumptions.

## Architecture decision

Fixed:

- audit current overlay/state/event dependencies before implementation
- new work targets Shadow DOM
- adapters are temporary and explicit
- legacy overlay-only behavior is marked transitional/deprecated

## Audit table

| Current UI/path | Current role | Canonical replacement | Decision | Blocker |
|---|---|---|---|---|
| legacy overlay panel | old UI state | Shadow DOM panel | adapt/deprecate | TBD |
| old event handler | event consume | typed event store | keep/adapt/block | TBD |
| old command sender | command | command dispatcher | keep/adapt/block | TBD |
| picker path | target selection | candidate UI | adapt/block | TBD |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE010-A-001 | Audit | list overlay entry points | complete |
| FE010-A-002 | Audit | list frontend event consumers | complete |
| FE010-A-003 | Audit | map legacy to canonical | decision per item |
| FE010-I-001 | Integration | canonical event not legacy-only | Shadow UI consumes |

## Edge cases

- both UIs mounted
- old event names only
- tests depend on legacy overlay
- hidden overlay side effects

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

First Codex task for FE-010 should be read-only:

```text
Read FE-010, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
