# BE-004 Active plan store and plan_ready ownership

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
**Blocks:** BE-005 confirmation gate, BE-006 execution contract, BE-007 correction diff  
**Version:** Batch 02 v1  

---

## Product contribution

Makes plan_ready a backend-owned active plan/version, not an LLM message or frontend preview. This lets backend know exactly which plan is corrected, confirmed, and executed.

This story contributes to the final Complete LLM Mode workflow by strengthening the backend-owned runtime truth path:

```text
user intent → plan/correction/confirmation → backend validation → execution/recording/replay/completion
```

## Parent Status

- Status: Done
- Progress: Done
- Reason: active-plan ownership, stale-confirm rejection, late-confirmation protection, and remaining versioning-gap audit are complete.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-004.1 Map active plan state ownership in backend | Done | commit `176cad2`; stale plan confirmation path grounded in backend state |
| BE-004.2 Store run_id/plan context on active plan | Done | commits `176cad2` and `6b03a82`; confirmation path is run-scoped |
| BE-004.3 Reject stale confirmations against active plan context | Done | commit `176cad2`; stale plan confirmation guard in `agent.py` |
| BE-004.4 Ensure late confirmation cannot reopen completed run | Done | commit `6b03a82`; late-confirmation rejection for completed runs |
| BE-004.5 Identify remaining active plan store/versioning gaps | Done | `agent.py` active-plan state and plan confirmation flow; `tests/test_backend_isolation_contract.py`, `tests/test_late_event_contract.py`, `tests/test_event_sequence_contract.py`; focused suite `58 passed, 1 xfailed` |

### Done Children

- `BE-004.1` Map active plan state ownership in backend
- `BE-004.2` Store run_id/plan context on active plan
- `BE-004.3` Reject stale confirmations against active plan context
- `BE-004.4` Ensure late confirmation cannot reopen completed run
- `BE-004.5` Identify remaining active plan store/versioning gaps

### In Progress Children

- None

### Remaining Planning Children

- None

## Evidence

- `agent.py` active-plan state ownership and plan confirmation flow were audited for remaining versioning gaps.
- `tests/test_backend_isolation_contract.py`, `tests/test_late_event_contract.py`, and `tests/test_event_sequence_contract.py` stay green in the focused backend sweep.
- The focused backend contract suite passed `58` tests with `1` xfailed.
- Branch status: branch-only on `dev1/backend-isolation-contract-tests`.

## Next Action

- None; BE-004 is complete.

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

| Layer | Relationship to BE-004 |
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
| Product Workflows | User can correct plan; revised plan shown; only corrected plan executes. | Plan identity/version/history are required. | Implement ActivePlan store. |
| SOURCE-001 | Backend owns plan mutation acceptance. | LLM plan text is proposal only. | Active plan mutation through backend only. |
| Handoff | Pending step identity remains stable through plan_ready/correction/confirmation/execution/recording. | Plan must preserve stable step/operation IDs where valid. | Store ordered plan children. |

---

## Architecture decision

Active plan is a backend object with plan_id/version/status. plan_ready is emitted from that object. Correction creates a new validated version. Confirmation locks current version.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | BE-005 confirmation gate, BE-006 execution contract, BE-007 correction diff | Cannot proceed safely without this story or approved mocks |
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
| ActivePlan | plan_id, run_id, version, status | draft/awaiting_confirmation/corrected/confirmed/rejected/cancelled | source for plan_ready |
| ActivePlanStep | step_id, parent_intent, expected_outcome_metadata, children | ordered parent step | source for execution contract |
| ActivePlanOperation | operation_id, step_id, type/subtype, target, locator_ref, order_index | ordered child operation | source for BE-006 |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE004-U-001 | Unit | create active plan | plan proposal | plan_id/version set | backend plan truth |
| BE004-U-002 | Unit | correction increments version | correction diff | version+history updated | stale safety |
| BE004-U-003 | Unit | stale confirm rejected | old version confirm | runtime_rejected | version safety |
| BE004-U-004 | Unit | discussion no mutation | chat message | active plan unchanged | no prose mutation |
| BE004-I-001 | Integration | plan_ready→correction→plan_ready | corrected plan | old plan cannot execute | correction path |

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
