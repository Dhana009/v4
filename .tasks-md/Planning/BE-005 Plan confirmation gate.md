# BE-005 Plan confirmation gate

**Type:** Story  
**Status:** Planning  
**Priority:** P0  
**Epic:** EPIC-001 Backend Runtime Truth  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Planning; versioning audit still open  
**Progress:** Mostly Done  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001  
**Blocks:** BE-006 execution contract, LLM Mode execution, BE-009 recording  
**Version:** Batch 02 v1  

---

## Product contribution

Turns plan review into a real safety gate. Browser-changing execution starts only after the backend validates explicit user confirmation for the current active plan/version.

This story contributes to the final Complete LLM Mode workflow by strengthening the backend-owned runtime truth path:

```text
user intent → plan/correction/confirmation → backend validation → execution/recording/replay/completion
```

## Parent Status

- Status: Planning
- Progress: Mostly Done
- Reason: confirmation gating, stale confirmation rejection, and legacy bare-confirm compatibility are covered; one remaining audit child stays open.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-005.1 Add confirmation gate contract tests | Done | commit `f117599`; `tests/test_event_sequence_contract.py`, `tests/test_late_event_contract.py` |
| BE-005.2 Require backend-owned confirmation before execution | Done | commit `176cad2`; `tests/test_event_sequence_contract.py` |
| BE-005.3 Reject stale confirmation against active run/plan context | Done | commits `176cad2`, `6b03a82`; `tests/test_late_event_contract.py` |
| BE-005.4 Preserve safe legacy bare confirmation compatibility | Done | `runtime/event_contracts.py` accepts confirmed commands with active run context; `tests/test_event_sequence_contract.py`, `tests/test_late_event_contract.py` |
| BE-005.5 Audit remaining confirmation/versioning gaps | In Progress | remaining confirmation/versioning audit in progress |

### Done Children

- `BE-005.1` Add confirmation gate contract tests
- `BE-005.2` Require backend-owned confirmation before execution
- `BE-005.3` Reject stale confirmation against active run/plan context
- `BE-005.4` Preserve safe legacy bare confirmation compatibility

### In Progress Children

- `BE-005.5` Audit remaining confirmation/versioning gaps

### Remaining Planning Children

- None

## Evidence

- Commit `f117599` added the core command/sequence contract coverage.
- Commit `176cad2` rejected stale plan confirmations.
- Commit `cd438d7` rejected stale backend commands.
- Commit `6b03a82` rejected late confirmations for completed runs.
- `tests/test_event_sequence_contract.py` and `tests/test_late_event_contract.py` cover the confirmation gate and stale/late cases.
- The latest focused backend set passed `47` tests.

## Next Action

- Close the remaining confirmation/versioning audit before moving BE-005 beyond Planning.

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

| Layer | Relationship to BE-005 |
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
| Product Workflows | User confirms revised plan; only confirmed plan executes. | Confirm must target current active version. | Validate confirm before execution. |
| Handoff | plan_ready is proposal before confirmation and must not mutate execution state. | plan_ready cannot execute. | Gate all browser-changing actions. |
| BE-004 | Active plan store owns plan_id/version. | Confirm validates active plan. | Reject stale confirm. |

---

## Architecture decision

`confirmed` is the only valid path from RunState.plan_review to RunState.executing. Duplicate, stale, missing-plan, clarification-open, recovery-open confirmations are rejected.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | BE-006 execution contract, LLM Mode execution, BE-009 recording | Cannot proceed safely without this story or approved mocks |
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
| ConfirmCommand | run_id, plan_id, plan_version | required | request to execute active plan |
| ConfirmationResult | accepted/rejected, current_state, rejection_code? | required | state transition or rejection |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE005-U-001 | Unit | plan_ready not execution | plan_ready | no browser action | confirmation gate |
| BE005-U-002 | Unit | valid confirm | current active plan | executing state | explicit confirmation |
| BE005-U-003 | Unit | stale confirm | old version | runtime_rejected | version safety |
| BE005-U-004 | Unit | duplicate confirm | already executing | no duplicate execution | idempotency |
| BE005-I-001 | Integration | LLM action before confirm | tool call | blocked | LLM proposes only |

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
