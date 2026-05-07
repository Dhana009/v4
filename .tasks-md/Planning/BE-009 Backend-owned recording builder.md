# BE-009 Backend-owned recording builder

**Type:** Story  
**Status:** Planning  
**Progress:** Partially Done  
**Priority:** P0  
**Epic:** EPIC-001 Backend Runtime Truth  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Selected child work in progress; recording/codegen verification pending  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001  
**Blocks:** code_update, recorded UI, BE-010 completion guard, BE-012 replay smoke  
**Version:** Batch 02 v1  

---

## Product contribution

Turns validated execution evidence into backend-owned recorded steps. This is the bridge from browser execution to deterministic Playwright codegen/replay.

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

| Layer | Relationship to BE-009 |
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
| SOURCE-001 | Backend owns recording truth and code_update trigger. | Recording cannot be model/frontend-owned. | Build recording builder. |
| Handoff | Recording model is parent recorded step with child operations/checks. | Preserve parent/child structure. | Build parent/child payload. |
| BE-006 | Execution contract validates children. | Record only validated child results. | Consume execution evidence. |
| BE-008 | Recovery/failure blocks recording. | Unresolved failure cannot record parent. | Reconcile child outcomes. |

---

## Architecture decision

Recording is built only after backend execution/assertion success evidence. Parent step contains ordered recorded children. expected_outcome remains parent metadata only.

## Parent Status

- Status: Planning
- Progress: Partially Done
- Reason: Recording-by-evidence is already covered by tests, but `code_update` still falls back to `generated_line` when child evidence is unresolved or failed.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-009.1 Add recording/codegen truth contract tests | Done | `tests/test_recording_codegen_truth_contract.py` covers parent metadata, child ordering, and code-update shape |
| BE-009.2 Prevent code_update from trusting generated_line without successful child evidence | In Progress | `agent.py` `_build_code_update_payload` still falls back to `generated_line` when child evidence is unresolved |
| BE-009.3 Preserve expected_outcome as parent metadata only | Done | `tests/test_recording_codegen_truth_contract.py` asserts children exclude `expected_outcome` and `observed_outcome` |
| BE-009.4 Preserve child operation order from execution evidence | Done | `tests/test_recording_codegen_truth_contract.py` and `tests/test_code_update.py` verify ordered child code lines |
| BE-009.5 Verify recording/codegen regression suite | Planning | Focused backend contract suite will run after the BE-009.2 fix |

### Done Children

- `BE-009.1` Add recording/codegen truth contract tests
- `BE-009.3` Preserve expected_outcome as parent metadata only
- `BE-009.4` Preserve child operation order from execution evidence

### In Progress Children

- `BE-009.2` Prevent code_update from trusting generated_line without successful child evidence

### Remaining Planning Children

- `BE-009.5` Verify recording/codegen regression suite

## Evidence

- `tests/test_recording_codegen_truth_contract.py` already covers the parent/child recording contract and the unresolved-child xfail gap.
- `agent.py` `_build_code_update_payload` still needs the narrow evidence-only fix.

## Next Action

- Patch `_build_code_update_payload`, remove the xfail, and run the focused recording/backend contract suite.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | code_update, recorded UI, BE-010 completion guard, BE-012 replay smoke | Cannot proceed safely without this story or approved mocks |
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
| RecordedStep | recorded_step_id, source_step_id, run_id, plan_id/version, parent_intent, expected_outcome_metadata, observed_outcome?, children, evidence_refs | required | recorded parent |
| RecordedChild | operation_id, type/subtype, locator?, input/value?, result, evidence_ref | required | recorded child |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE009-U-001 | Unit | record after all children success | child results success | recorded parent | evidence recording |
| BE009-U-002 | Unit | required child failed | failed child | no record/recovery | child reconciliation |
| BE009-U-003 | Unit | LLM emits step_recorded | model output | ignored | backend recording |
| BE009-U-004 | Unit | expected_outcome leakage | metadata present | not assertion target | metadata rule |
| BE009-I-001 | Integration | execution→recording | BE-006 success | step_recorded event-ready | lifecycle |

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
