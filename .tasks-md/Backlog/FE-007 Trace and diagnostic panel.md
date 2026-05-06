# FE-007 Trace and diagnostic panel

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** FE-002, EVENT-003, EVENT-010, LLM-010  
**Blocks:** debuggability, E2E evidence review  
**Version:** Batch 06 v1  

---

## Product contribution

This story exposes enough trace/diagnostic data for users and developers to understand what happened.

## Architecture decision

Fixed:

- trace panel renders backend/telemetry evidence
- does not invent runtime state
- rejection/failure/telemetry entries are structured
- large payloads are summarized or linked by evidence_ref

## Trace sources

| Source | Examples |
|---|---|
| runtime events | run_started, plan_ready, step_failed |
| rejections | runtime_rejected |
| LLM telemetry | purpose/model/tokens/latency |
| DOM evidence | locator validation result |
| replay | replay_result |
| capability gap | capability_gap_recorded |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE007-U-001 | Unit | runtime_rejected | diagnostic row |
| FE007-U-002 | Unit | LLM telemetry | telemetry row |
| FE007-U-003 | Unit | evidence_ref | link/reference shown |
| FE007-I-001 | Integration | failure flow | trace explains blocker |

## Edge cases

- huge trace list
- missing evidence_ref
- telemetry failure warning
- sensitive data redaction need

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

First Codex task for FE-007 should be read-only:

```text
Read FE-007, SOURCE-001, PLAN-002, PLAN-005, EPIC-005, EPIC-002, EVENT-001, EVENT-002, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
