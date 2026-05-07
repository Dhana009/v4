# EVENT-002 Frontend command envelope

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-002 Typed Event Contract  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** BE-001, BE-003, EPIC-002  
**Blocks:** EVENT-003, plan/correction/replay command stories, DEV-3 command UI  
**Version:** Batch 03 v1  

---

## Product contribution

This story defines the frontend-to-backend command envelope. It makes every UI/user command an explicit backend-validated request.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| SOURCE-001 | frontend collects input; backend owns truth | commands cannot mutate state directly |
| BE-003 | commands are schema/state validated | define command envelope |
| Frontend/UI Spec | UI sends confirm/correction/skip/stop | stable command payloads needed |

## Architecture decision

Fixed:

- every command has `type`, `command_id`, `source`, and target identity where applicable
- command payload cannot include direct runtime truth mutation fields
- backend validates shape and state before mutation

## Command envelope contract

| Field | Required | Meaning |
|---|---|---|
| type | Yes | canonical command name |
| command_id | Yes | idempotency/correlation |
| schema_version | Yes | contract version |
| source | Yes | frontend/user/system |
| run_id | Conditional | active run scope |
| plan_id/plan_version | Conditional | plan commands |
| step_id/operation_id | Conditional | step/op commands |
| payload | Yes | command-specific body |
| requested_at | Optional | frontend timestamp |
| trace_id | Optional | diagnostic correlation |

## Canonical command families

```text
run_steps / llm_run
confirmed
correction
option_selected
replay_step
replay_operation
replay_all
skip_step
stop_run
save_session
load_session
update_locator
```

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| EVT002-C-001 | Contract | valid confirmed command | accepted |
| EVT002-C-002 | Contract | command missing type | rejected |
| EVT002-C-003 | Contract | command attempts status=completed | rejected |
| EVT002-C-004 | Contract | stale plan command | rejected by validation |
| EVT002-I-001 | Integration | UI command through bridge | backend receives canonical command |

## Edge cases

- duplicate command_id
- command sent after run stopped
- command references old plan_version
- replay command during execution
- save/load command unsupported in P0

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

First Codex task for EVENT-002 should be read-only:

```text
Read EVENT-002, SOURCE-001, PLAN-002, PLAN-005, EPIC-002, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current event/command ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
