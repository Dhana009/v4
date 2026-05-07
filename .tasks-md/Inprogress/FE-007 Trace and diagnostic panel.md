# FE-007 Trace and diagnostic panel

**Type:** Story  
**Status:** In Progress  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Frontend inspection complete; frontend-only trace slice implemented and awaiting board transition  
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

## Subtasks

- source-rule mapping
- DEV-4 artifact/evidence output inventory
- frontend trace event/read-model expectations
- trace display-only rules
- redaction status display expectations
- artifact link/manifest summary display expectations if metadata exists
- negative cases: trace rows must not mutate lifecycle/runtime state
- boundary cases: missing evidence_ref, redaction warning, unsupported/unknown trace row, absent optional artifact
- test-only slice
- narrow frontend implementation slice
- explicit remaining backend/exporter dependency
- verification commands
- stop conditions

## Delivery notes

- Frontend-only trace display slice implemented: render backend/evidence metadata as read-only trace rows.
- Trace rows are display-only and do not mutate runState, interactionMode, recordedSteps, codePreview, or pending command truth.
- `traceEntries` are sourced from backend/evidence messages through the frontend read model and rendered in the Shadow DOM debug pane.
- Backend/exporter/redaction work remains outside this slice and is still required for the full FE-007 story.
- Remaining dependency: exporter-fed artifact manifests, redaction report output, and full evidence bundle validation from DEV-4/backend work.

## Verification

- Added: `tests/test_frontend_trace_display.py`
- Focused suite: `tests/test_frontend_trace_display.py tests/test_frontend_accessibility_focus.py tests/test_frontend_event_command_contract.py tests/test_e2e_harness.py -q`
- Result: `68 passed`
- Build: `cd frontend && npm run build`
- Result: passed
- No backend/runtime/LLM/DOM changes

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
