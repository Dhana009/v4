# FE-004 LLM Mode plan review UI

**Type:** Story  
**Status:** Inprogress  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Repo inspection complete; test-first implementation in progress  
**Dependencies:** FE-002, FE-003, EVENT-004, BE-004, BE-005  
**Blocks:** confirmation/correction user workflow, E2E plan review  
**Version:** Batch 06 v1  

---

## Product contribution

This story builds the plan review UI where the user can inspect, confirm, or correct the backend-owned plan.

## Architecture decision

Fixed:

- renders `plan_ready` from backend active plan
- confirm command includes run_id/plan_id/plan_version
- correction command does not mutate local plan directly
- revised plan renders only after backend accepts correction

## Subtasks

- [ ] source-rule mapping
- [ ] existing frontend/backend event coverage inventory
- [ ] plan_ready rendering expectations
- [ ] runtime_rejected display expectations
- [ ] command actions available from this UI state
- [ ] negative cases: unknown/malformed/missing payloads must not fake lifecycle truth
- [ ] boundary cases: stale run_id, duplicate events, correction races
- [ ] test-only slice
- [ ] narrow implementation slice
- [ ] verification commands
- [ ] stop conditions

## UI states

| State | Source |
|---|---|
| no plan | backend state |
| plan ready | plan_ready |
| correction pending | command in flight |
| stale/rejected | runtime_rejected |
| confirmed/executing | backend event/store |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE004-U-001 | Unit | render plan_ready | steps visible |
| FE004-U-002 | Unit | confirm plan | confirmed command with version |
| FE004-U-003 | Unit | correction submit | correction command |
| FE004-U-004 | Unit | stale rejection | shown to user |
| FE004-I-001 | Integration | correction then revised plan | old plan not rendered as active |

## Edge cases

- plan with many steps
- duplicate confirm
- correction while executing
- stale plan_version

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

First Codex task for FE-004 should be read-only:

```text
Read FE-004, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
