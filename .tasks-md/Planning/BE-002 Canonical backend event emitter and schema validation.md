# BE-002 Canonical backend event emitter and schema validation

**Type:** Story  
**Status:** Planning  
**Priority:** P0  
**Epic:** EPIC-001 Backend Runtime Truth  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Planning; schema-gap child still open  
**Progress:** Mostly Done  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001  
**Blocks:** DEV-3 frontend lifecycle rendering, DEV-4 event capture, BE-003 rejection flow, BE-010 run_completed event  
**Version:** Batch 02 v1  

---

## Product contribution

Creates the canonical backend event layer so frontend, E2E, trace, recording/replay, and user-facing state render from typed backend truth instead of logs, LLM prose, or ad hoc WebSocket payloads.

This story contributes to the final Complete LLM Mode workflow by strengthening the backend-owned runtime truth path:

```text
user intent → plan/correction/confirmation → backend validation → execution/recording/replay/completion
```

## Parent Status

- Status: Planning
- Progress: Mostly Done
- Reason: the backend event contract tests, event seam, and session-state handshake are in place, but the remaining schema-gap child keeps the parent in Planning.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-002.1 Add backend event contract tests | Done | commit `f117599`; `tests/test_event_contract.py`, `tests/test_event_sequence_contract.py` |
| BE-002.2 Add canonical backend event helper/seam | Done | commit `f7e3847`; `runtime/event_contracts.py`, `agent.py`, `server.py` |
| BE-002.3 Add explicit run_completed event contract | Done | covered by `f7e3847` contract seam and the event-contract suite |
| BE-002.4 Add explicit recovery_needed event contract | Done | covered by `f7e3847` contract seam and the event-contract suite |
| BE-002.5 Add session_state websocket event contract | Done | commits `f7e1c61` and `680aa8f`; websocket/session-state handshake and status update |
| BE-002.6 Identify remaining canonical event envelope/schema gaps | Planning | remaining schema-gap child |

### Done Children

- `BE-002.1` Add backend event contract tests
- `BE-002.2` Add canonical backend event helper/seam
- `BE-002.3` Add explicit run_completed event contract
- `BE-002.4` Add explicit recovery_needed event contract
- `BE-002.5` Add session_state websocket event contract

### Remaining Planning Children

- `BE-002.6` Identify remaining canonical event envelope/schema gaps

## Evidence

- Commit `f117599` added backend event contract coverage tests.
- Commit `f7e3847` introduced `runtime/event_contracts.py` and the backend event/command seam.
- Commit `f7e1c61` emitted `session_state` on websocket connect and was merged to local main at `908f4d0`.
- Commit `680aa8f` updated the session state contract status.
- Focused verification passed `43` backend/event tests and `11` websocket/session tests.

## Next Action

- Close the final schema-gap audit and confirm no additional canonical event envelopes are missing before moving the parent story out of Planning.

---

## Final product workflow supported

| Workflow stage | How this story contributes |
|---|---|
| plan/review | protects backend-owned plan/state boundaries |
| execution | prevents unsafe or stale runtime mutation |
| recovery/recording/completion | preserves evidence-based backend truth |
| frontend/E2E | gives DEV-3 and DEV-4 stable contracts to render/assert |

---

## System role

| Layer | Relationship to BE-002 |
|---|---|
| Backend | Primary owner and source of truth |
| LLM | Proposes only; cannot own runtime truth |
| Frontend | Renders backend events/commands only |
| E2E Harness | Verifies contract behavior and evidence |
| Trace | Captures accepted/rejected paths |

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| SOURCE-001 | Every important lifecycle change must become a typed backend event. | State changes cannot remain only in logs or frontend assumptions. | Define event factory/schema validation. |
| Backend Event Contract | Canonical events include plan_ready, clarification_needed, recovery_needed, step_validating, step_executing, step_recorded, step_failed, step_skipped, code_update, replay_started, replay_result, run_completed, session_state, capability_gap_recorded. | Frontend and E2E need stable event names/payloads. | New backend work emits canonical names; adapters are temporary only. |
| BE-001 | State transitions are backend-owned and event-compatible. | Events expose state truth, not create it. | Consume transition results and serialize them safely. |

---

## Architecture decision

Backend event factory validates event type and required identifiers before emission. Runtime truth events are produced from backend state transitions. LLM/frontend cannot emit runtime-truth events directly.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | DEV-3 frontend lifecycle rendering, DEV-4 event capture, BE-003 rejection flow, BE-010 run_completed event | Cannot proceed safely without this story or approved mocks |
| Indirect consumers | EPIC-005 frontend, EPIC-006 E2E, EPIC-008 recording/codegen, EPIC-009 trace | Eventually depend on this contract |
| Parallel safe with mocks | DEV-2 LLM policy planning, DEV-3 Shadow DOM shell, DEV-4 harness skeleton | May proceed only without inventing final backend truth |
| Conflict zones | `agent.py`, WebSocket command/event paths, runtime state, frontend lifecycle store | Inspect before editing |

---

## What BE-001 unlocks for this story

SOURCE-001, PLAN-002, PLAN-005, EPIC-001, and BE-001 are upstream planning sources. BE-001 provides the backend runtime state, status mapping, transition/rejection model, and StepState → OperationState reconciliation that every BE-002 to BE-012 story must use.

---

## What this story unlocks downstream

This story unlocks downstream implementation by producing a precise backend contract that later stories, frontend rendering, LLM schema validation, and E2E assertions can consume without guessing.

---

## Four-developer coordination

| Developer | Relationship to this story |
|---|---|
| DEV-1 Backend | Primary owner; performs repo inspection and backend implementation |
| DEV-2 LLM | Must align schemas/proposals with backend validation; cannot own truth |
| DEV-3 Frontend | Can mock/render the resulting events/states/commands; cannot infer truth |
| DEV-4 E2E | Builds tests and artifact capture around this contract |

---

## Contract/schema

| Item | Required fields | Rules | Used by |
|---|---|---|---|
| run_started | run_id | status, started_at | RunState.planning |
| plan_ready | run_id, plan_id, plan_version | steps, summary, status | PlanState.awaiting_confirmation |
| clarification_needed | run_id, clarification_id | question, options, reason | RunState.clarification |
| step_validating | run_id, step_id, operation_id? | target/locator context | OperationState.validating |
| step_executing | run_id, step_id, operation_id | operation type/subtype | OperationState.executing |
| step_failed/recovery_needed | run_id, step_id, operation_id? | error_summary, options | RunState.recovery |
| step_recorded | run_id, step_id | recorded parent/children | RecordingState |
| run_completed | run_id | summary/counts | RunState.completed |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE002-C-001 | Contract | valid plan_ready | PlanState.awaiting_confirmation | event accepted | typed events |
| BE002-C-002 | Contract | missing type | payload without type | rejected | schema validation |
| BE002-C-003 | Contract | unknown event type | unsupported type | rejected | canonical names |
| BE002-C-004 | Contract | step event missing step_id | step_executing without step_id | rejected | identity |
| BE002-C-005 | Contract | runtime_rejected shape | rejection payload | accepted | structured rejection |
| BE002-I-001 | Integration | invalid event blocked | bad event through bridge | not emitted | frontend safety |

---

## Edge / negative cases

- stale plan/version references
- duplicate terminal transitions
- missing run_id/step_id/operation_id where required
- frontend attempts to mutate runtime truth
- LLM prose claims success/completion
- current code conflicts with source contract
- broad rewrite appears necessary
- unsupported capability would be guessed instead of rejected or recorded

---

## Acceptance criteria

- Story contract is implemented through backend-owned validation.
- Invalid inputs fail closed with structured evidence.
- No LLM/frontend path owns runtime truth.
- Focused tests are added and pass.
- Repo-inspection report confirms narrow implementation path.
- Downstream contracts remain compatible with PLAN-002 and EPIC-001.


---

## Required skills

```text
.autoworkbench/skills/00_skill_usage_policy.md
.autoworkbench/skills/00_architecture_contract.md
.autoworkbench/skills/01_prd_scope_validation.md
.autoworkbench/skills/backend_step_runner.md
.autoworkbench/skills/typed_event_contract.md
.autoworkbench/skills/02_tdd_regression_harness.md
.autoworkbench/skills/03_refactor_safety.md
```

## Allowed areas

After repo inspection only:
- focused backend runtime modules related to this story
- focused tests for this story
- narrow extraction from existing lifecycle code if required

Exact files must be named by repo inspection.

## Forbidden areas

Do not modify frontend product UI, LLM prompt/persona/policy routing unless explicitly part of schema boundary, codegen/replay repair implementation unless explicitly scoped, PRD/spec/skill files, broad `agent.py` flow unless approved, or unrelated product/test code.

## Repo-inspection report template

```markdown
# Repo Inspection Report — <Story ID>

## 1. Files inspected
- ...

## 2. Current behavior observed
- ...

## 3. Current ownership map
| Concern | Current file/function/module | Notes |
|---|---|---|
| lifecycle state | ... | ... |
| active plan | ... | ... |
| command handling | ... | ... |
| event emission | ... | ... |
| recording/replay | ... | ... |

## 4. Existing tests found
- ...

## 5. Source alignment check
| Source rule | Current implementation status | Gap |
|---|---|---|

## 6. Proposed narrow implementation path
- ...

## 7. Tests to add first
- ...

## 8. Files likely to change
- ...

## 9. Files explicitly not to change
- ...

## 10. Risks / blockers
- ...

## 11. Ready for implementation?
Yes/No, with reason.
```

## Stop conditions

Stop if source evidence is missing or contradictory, current code conflicts and migration path is unclear, tests cannot be written first, implementation requires broad rewrite, LLM/frontend would own runtime truth, backend identity cannot be preserved, event/command/schema boundary is ambiguous, or this story would silently alter another workstream contract.

## Codex comprehension checklist

After reading this story, Codex should explain product contribution, upstream/downstream dependencies, direct vs indirect blockers, parallel work, schema/contract, tests, repo-inspection output, forbidden scope, and stop conditions.
