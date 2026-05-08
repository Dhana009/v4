# FE-001 Shadow DOM host and mount lifecycle

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-005, EVENT-001  
**Blocks:** FE-002, FE-003, FE-004 to FE-009  
**Version:** Batch 06 v1  

---

## Product contribution

This story creates the stable frontend host where Complete LLM Mode UI lives.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| Frontend/UI Spec | Shadow DOM host is primary target | build/audit Shadow DOM mount |
| SOURCE-001 | frontend renders backend truth | host must not own runtime state |
| PLAN-005 | E2E needs stable hooks | host needs predictable root/test id |

## Architecture decision

Fixed:

- Shadow DOM host is primary UI root
- mount/unmount is explicit and safe
- product page styles should not break UI
- UI should not pollute target page DOM semantics
- legacy overlay remains transitional

## Host contract

| Field/behavior | Required |
|---|---|
| root id/test hook | Yes |
| shadow root creation | Yes |
| mount status | visible/hidden/mounted/unmounted |
| isolation | page CSS should not leak in |
| cleanup | unmount removes listeners/root safely |
| error boundary | render safe failure state |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE001-U-001 | Unit | mount host | root created |
| FE001-U-002 | Unit | duplicate mount | no duplicate root |
| FE001-U-003 | Unit | unmount | cleanup complete |
| FE001-I-001 | Integration | page CSS conflict | UI isolated |
| FE001-E-001 | E2E | host appears on fixture page | stable selector |

## Edge cases

- route/page navigation
- product page CSP/style interference
- duplicate injection
- host hidden/collapsed

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

First Codex task for FE-001 should be read-only:

```text
Read FE-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
