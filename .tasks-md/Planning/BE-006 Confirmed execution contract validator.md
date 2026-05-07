# BE-006 Confirmed execution contract validator

**Type:** Story  
**Status:** Planning  
**Priority:** P0  
**Epic:** EPIC-001 Backend Runtime Truth  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Planning; strict cursor audit still open  
**Progress:** Partially Done  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001  
**Blocks:** BE-009 recording builder, execution E2E, code_update correctness  
**Version:** Batch 02 v1  

---

## Product contribution

Makes the confirmed plan the execution contract. Prevents LLM/tool execution from running a different operation than what user confirmed.

This story contributes to the final Complete LLM Mode workflow by strengthening the backend-owned runtime truth path:

```text
user intent → plan/correction/confirmation → backend validation → execution/recording/replay/completion
```

## Parent Status

- Status: Planning
- Progress: Partially Done
- Reason: confirmed execution boundaries, pre-confirmation execution blocking, stale run rejection, and recovery blocking are covered; strict cursor gaps remain open.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-006.1 Map confirmed execution contract boundaries | Done | commit `f7e3847`; `agent.py` confirmed execution check; `tests/test_event_sequence_contract.py` |
| BE-006.2 Add tests that execution cannot start before confirmation | Done | `tests/test_event_sequence_contract.py`, `tests/test_completion_guard.py` |
| BE-006.3 Add tests for stale run/plan rejection before execution | Done | `tests/test_backend_isolation_contract.py`, `tests/test_late_event_contract.py` |
| BE-006.4 Ensure unresolved recovery blocks finality/execution continuation | Done | `tests/test_completion_guard.py`, `tests/test_recovery_scope_guard.py` |
| BE-006.5 Identify remaining strict execution cursor gaps | Planning | remaining strict-cursor audit child |

### Done Children

- `BE-006.1` Map confirmed execution contract boundaries
- `BE-006.2` Add tests that execution cannot start before confirmation
- `BE-006.3` Add tests for stale run/plan rejection before execution
- `BE-006.4` Ensure unresolved recovery blocks finality/execution continuation

### Remaining Planning Children

- `BE-006.5` Identify remaining strict execution cursor gaps

## Evidence

- Commit `f117599` added backend command/sequence contract coverage.
- Commit `f7e3847` added the backend command validation seam that execution checks consume.
- Commit `176cad2` rejected stale plan confirmations.
- Commit `1b8c084` isolated backend recovery state between runs.
- Related tests include `tests/test_event_sequence_contract.py`, `tests/test_completion_guard.py`, `tests/test_recovery_scope_guard.py`, and `tests/test_backend_isolation_contract.py`.
- The latest focused backend set passed `47` tests.

## Next Action

- Finish the strict execution-cursor gap audit before moving BE-006 beyond Planning.

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

| Layer | Relationship to BE-006 |
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
| SOURCE-001 | Backend owns execution contract. | LLM proposes; backend validates. | Validate each execution attempt. |
| Handoff | Confirmed plan children become execution contract; strict cursor prevents cross-step contamination. | Need current step/operation cursor. | Validate identity and order. |
| BE-005 | Confirmation locks active plan version. | Only confirmed plan can execute. | Build contract from confirmed version. |

---

## Architecture decision

Every browser action/assertion must match the next expected confirmed operation by run_id, plan_id/version, step_id, operation_id, type/subtype, target/locator, and assertion data.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | BE-009 recording builder, execution E2E, code_update correctness | Cannot proceed safely without this story or approved mocks |
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
| ConfirmedExecutionContract | run_id, plan_id/version, ordered_step_ids, current cursors, status | required | execution authority |
| ContractOperation | operation_id, step_id, type/subtype, target, locator_ref, expected_value | required | validation target |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE006-U-001 | Unit | expected op allowed | matching op | allowed | contract validation |
| BE006-U-002 | Unit | wrong operation_id | mismatch | rejected | child identity |
| BE006-U-003 | Unit | wrong step_id | mismatch | rejected | step isolation |
| BE006-U-004 | Unit | wrong assertion value | mismatch | rejected | assertion semantics |
| BE006-U-005 | Unit | cursor advances only on success | LLM says success | no advance | backend evidence |
| BE006-I-001 | Integration | multi-step isolation | op from step 2 during step 1 | rejected | no contamination |

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
