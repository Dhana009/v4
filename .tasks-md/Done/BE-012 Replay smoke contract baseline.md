# BE-012 Replay smoke contract baseline

Status: Done  
Sprint: Sprint 0  


**Type:** Story  
**Status:** Done  
**Progress:** Done  
**Priority:** P0  
**Epic:** EPIC-001 Backend Runtime Truth  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; all child tasks complete  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001  
**Blocks:** Replay P1 foundation, E2E replay smoke, recorded-step validation  
**Version:** Batch 02 v1  

---

## Product contribution

Establishes minimal backend-owned replay path. P0 needs replay smoke and precondition guard, not robust replay repair.

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

| Layer | Relationship to BE-012 |
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
| SOURCE-001 | Replay is backend operation, not frontend simulation. | Backend owns replay state/result. | Implement replay smoke. |
| PLAN-003 | P0 includes replay smoke; robust repair is P1. | Keep scope narrow. | No broad replay repair. |
| BE-009 | Recording builder provides recorded steps/children. | Replay consumes recorded evidence. | Use recorded payload. |
| BE-010 | Terminal state indicates readiness. | Replay targets terminal recorded steps. | Validate preconditions. |

---

## Architecture decision

Replay commands are backend-validated, use separate ReplayState, check preconditions, emit typed replay result, and avoid auto repair/versioning in P0.

## Parent Status

- Status: Done
- Progress: Done
- Reason: Replay smoke and precondition coverage are covered by backend contract tests, and broad repair remains deferred to the P1 roadmap.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-012.1 Add replay smoke contract tests | Done | `tests/test_replay_one.py` and `tests/test_replay_all.py` already provide the smoke baseline; the focused suite passed `59 passed` |
| BE-012.2 Verify replay one parent step uses recorded evidence | Done | `tests/test_replay_one.py::test_replay_one_resolves_recorded_step_by_step_id_and_executes_operations_in_order` |
| BE-012.3 Verify replay operation targets child operation safely | Done | `tests/test_replay_one.py::test_replay_one_stops_on_first_failed_child_action` and unsupported-action coverage |
| BE-012.4 Verify replay failure does not mutate recording unless repair is validated | Done | `tests/test_replay_all.py::test_replay_all_does_not_mutate_recorded_payload_or_code_payload_state` |
| BE-012.5 Verify unsupported/broader replay repair remains deferred, not faked | Done | `GOV-003` keeps robust replay repair in the roadmap; BE-012 remains smoke-only |

### Done Children

- `BE-012.1` Add replay smoke contract tests
- `BE-012.2` Verify replay one parent step uses recorded evidence
- `BE-012.3` Verify replay operation targets child operation safely
- `BE-012.4` Verify replay failure does not mutate recording unless repair is validated
- `BE-012.5` Verify unsupported/broader replay repair remains deferred, not faked

## Evidence

- `tests/test_replay_one.py` and `tests/test_replay_all.py` already cover replay smoke, precondition safety, and mutation isolation.
- `GOV-003` keeps broad replay repair explicitly outside the BE-012 P0 smoke contract.
- Focused backend contract suite passed `59 passed`.
- Branch status: branch-only on `dev1/backend-isolation-contract-tests`.

## Next Action

- None.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | Replay P1 foundation, E2E replay smoke, recorded-step validation | Cannot proceed safely without this story or approved mocks |
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
| ReplayState | replay_run_id, source_run_id?, target_step_id?, target_operation_id?, precondition_status, replay_status, result_summary?, evidence_ref? | required | replay truth |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE012-U-001 | Unit | replay unknown step | missing recorded step | rejected | command validation |
| BE012-U-002 | Unit | wrong page precondition | url mismatch | precondition fail | replay safety |
| BE012-U-003 | Unit | replay does not mutate live run | live run active | rejected/isolated | state separation |
| BE012-I-001 | Integration | replay one smoke | recorded click/assert | replay passes | P0 replay |

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
