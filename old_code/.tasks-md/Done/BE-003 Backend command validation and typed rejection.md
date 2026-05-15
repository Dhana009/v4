# BE-003 Backend command validation and typed rejection

Status: Done  
Sprint: Sprint 0  


**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-001 Backend Runtime Truth  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; all child tasks complete  
**Progress:** Done  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001  
**Blocks:** BE-004 active plan validation, BE-005 confirmation, BE-007 correction, BE-012 replay commands  
**Version:** Batch 02 v1  

---

## Product contribution

Ensures frontend/user commands are requests to the backend, not direct mutations of runtime truth. This protects confirm, correction, replay, skip, stop, and update_locator flows.

This story contributes to the final Complete LLM Mode workflow by strengthening the backend-owned runtime truth path:

```text
user intent → plan/correction/confirmation → backend validation → execution/recording/replay/completion
```

## Parent Status

- Status: Done
- Progress: Done
- Reason: command contract coverage, typed rejection, stale-command rejection, process-boundary coverage, and remaining validation-gap audit are complete.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-003.1 Add command contract tests | Done | commit `f117599`; `tests/test_command_contract.py` |
| BE-003.2 Add runtime_rejected typed payload | Done | commit `f7e3847`; `runtime/event_contracts.py` |
| BE-003.3 Add server-side command validation boundary | Done | commit `f7e3847`; `agent.py`, `server.py` |
| BE-003.4 Reject stale confirmed/correction commands by run_id | Done | commit `cd438d7`; stale backend command rejection in `agent.py` |
| BE-003.5 Add process-boundary malformed/unknown command tests | Done | commit `2011da2`; `tests/test_process_boundary_contract.py` |
| BE-003.6 Identify any remaining command validation gaps | Done | `runtime/event_contracts.py`, `agent.py`, `tests/test_command_contract.py`, `tests/test_late_event_contract.py`, `tests/test_process_boundary_contract.py`; focused suite `58 passed, 1 xfailed` |

### Done Children

- `BE-003.1` Add command contract tests
- `BE-003.2` Add runtime_rejected typed payload
- `BE-003.3` Add server-side command validation boundary
- `BE-003.4` Reject stale confirmed/correction commands by run_id
- `BE-003.5` Add process-boundary malformed/unknown command tests
- `BE-003.6` Identify any remaining command validation gaps

### In Progress Children

- None

### Remaining Planning Children

- None

## Evidence

- `runtime/event_contracts.py` and `agent.py` command validation paths were audited for remaining gaps.
- `tests/test_command_contract.py`, `tests/test_late_event_contract.py`, and `tests/test_process_boundary_contract.py` stay green in the focused backend sweep.
- The focused backend contract suite passed `58` tests with `1` xfailed.
- Branch status: branch-only on `dev1/backend-isolation-contract-tests`.

## Next Action

- None; BE-003 is complete.

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

| Layer | Relationship to BE-003 |
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
| SOURCE-001 | Frontend collects input; backend owns truth. | Commands request state change but do not own it. | Validate commands before mutation. |
| Backend Event Contract | Commands include run_steps/llm_run, confirmed, correction, option_selected, replay_step, replay_operation, replay_all, skip_step, stop_run, save_session, load_session, update_locator. | Backend needs canonical command schemas. | Define validation/rejection paths. |
| BE-001 | Runtime state determines legal transitions. | Commands validate against RunState/PlanState/StepState/OperationState. | Accept/reject based on current state. |
| BE-002 | Invalid command should return typed evidence. | Use runtime_rejected payload. | No free-form errors only. |

---

## Architecture decision

All commands are schema-validated and state-validated before runtime mutation. Unsupported, stale, malformed, or state-incompatible commands fail closed with typed rejection evidence.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | BE-004 active plan validation, BE-005 confirmation, BE-007 correction, BE-012 replay commands | Cannot proceed safely without this story or approved mocks |
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
| run_steps/llm_run | intent or steps | no conflicting active run unless explicit policy | creates planning state |
| confirmed | run_id, plan_id/version | RunState.plan_review + current PlanState | moves to execution path |
| correction | run_id, plan_id/version, message/diff | plan_review and current version | routes to BE-007 |
| skip_step | run_id, step_id, reason | step not already terminal | terminal skipped path |
| stop_run | run_id | non-terminal run | stopped |
| replay_step/operation/all | recorded target | no active live execution unless policy allows | replay path |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE003-C-001 | Contract | command missing type | payload no type | rejected | schema |
| BE003-U-001 | Unit | confirm without active plan | confirmed command | runtime_rejected | active plan truth |
| BE003-U-002 | Unit | stale confirm | old plan_version | rejected | version safety |
| BE003-U-003 | Unit | skip without reason | skip_step | rejected | explicit terminal |
| BE003-U-004 | Unit | frontend completion mutation | status=completed | rejected | frontend renders only |
| BE003-I-001 | Integration | valid confirm path | plan_review + confirmed | accepted transition | confirmation |

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


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
