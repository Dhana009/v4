# BE-010 Completion guard and run_completed contract

**Type:** Story  
**Status:** Planning  
**Progress:** Mostly Done  
**Priority:** P0  
**Epic:** EPIC-001 Backend Runtime Truth  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Selected audit child in progress; completion guard verification pending  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001  
**Blocks:** frontend final state, E2E completion assertions, replay smoke  
**Version:** Batch 02 v1  

---

## Product contribution

Prevents false success. `run_completed` is emitted only when every required step is terminal and no clarification, confirmation, execution, recovery, or recording blocker remains.

This story contributes to the final Complete LLM Mode workflow by strengthening the backend-owned runtime truth path:

```text
user intent → plan/correction/confirmation → backend validation → execution/recording/replay/completion
```

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

| Layer | Relationship to BE-010 |
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
| SOURCE-001 | Backend owns completion/failure truth. | Completion is backend decision. | Implement completion guard. |
| Handoff | run_completed cannot emit while unresolved states remain. | Check all blockers. | Guard terminal event. |
| BE-008 | Recovery blocks completion. | unresolved_failure prevents success. | Check recovery. |
| BE-009 | Recording evidence required. | Successful steps must be recorded. | Check recording. |

---

## Architecture decision

Completion is explicit backend guard. Duplicate completion is idempotent/no-op or structured rejection. Frontend/LLM cannot mark completion.

## Parent Status

- Status: Planning
- Progress: Mostly Done
- Reason: Completion guard, run_completed shape, late-confirmation rejection, and recovery blocking are already covered; the final audit child is selected for active verification.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-010.1 Verify run_completed is emitted once | Done | `tests/test_late_event_contract.py::test_run_completed_event_is_emitted_only_once_for_same_run` |
| BE-010.2 Verify unresolved recovery blocks completion | Done | `tests/test_completion_guard.py::test_pending_recovery_blocks_completion` |
| BE-010.3 Verify completed run rejects late confirmation | Done | `tests/test_late_event_contract.py::test_completed_run_rejects_late_confirmation_and_does_not_reopen_plan` |
| BE-010.4 Verify completion state does not leak across runs | Done | `tests/test_recovery_scope_guard.py` and `tests/test_completion_guard.py` keep completion/recovery state isolated |
| BE-010.5 Final completion guard audit | In Progress | Focused backend contract suite will verify completion guard remains stable after BE-009 |

### Done Children

- `BE-010.1` Verify run_completed is emitted once
- `BE-010.2` Verify unresolved recovery blocks completion
- `BE-010.3` Verify completed run rejects late confirmation
- `BE-010.4` Verify completion state does not leak across runs

### In Progress Children

- `BE-010.5` Final completion guard audit

### Remaining Planning Children

- None

## Evidence

- `tests/test_completion_guard.py` and `tests/test_late_event_contract.py` already prove the completion contract and idempotent `run_completed` emission.
- `tests/test_recovery_scope_guard.py` keeps recovery state from leaking into completion logic.

## Next Action

- Run the focused backend suite and keep the completion guard evidence aligned with the BE-009 fix.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | frontend final state, E2E completion assertions, replay smoke | Cannot proceed safely without this story or approved mocks |
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
| CompletionCheck | run_id, plan_id/version, terminal step counts, unresolved_failure?, pending_clarification?, active_operation? | required | completion decision |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE010-U-001 | Unit | all recorded | all terminal | run_completed allowed | backend completion |
| BE010-U-002 | Unit | recovery open | unresolved_failure | rejected | recovery blocks |
| BE010-U-003 | Unit | clarification pending | pending_clarification | rejected | no guessing |
| BE010-U-004 | Unit | operation executing | active_operation | rejected | execution truth |
| BE010-U-005 | Unit | duplicate completion | already completed | idempotent/no duplicate | terminal safety |
| BE010-I-001 | Integration | execution→recording→complete | all steps recorded | run_completed event-ready | lifecycle |

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
