# BE-011 Capability gap event baseline

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
**Blocks:** advanced capability backlog, trace observability, unsupported action handling  
**Version:** Batch 02 v1  

---

## Product contribution

Records unsupported capabilities as typed backend gaps instead of guessing, silently failing, or pretending unsupported actions succeeded.

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

| Layer | Relationship to BE-011 |
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
| SOURCE-001 | Unsupported behavior should become capability gap truth. | Backend records gap instead of guessing. | Define capability_gap_recorded baseline. |
| PLAN-003 | Advanced capabilities are P1; P0 tracks baseline gaps. | Do not implement all advanced behavior here. | Record evidence only. |
| BE-002 | canonical event layer. | Gap becomes typed event. | Emit/validate gap payload. |

---

## Architecture decision

P0 records capability gaps; it does not implement upload/download/popup/iframe/network/auth support broadly. Gap has needed capability, impact, evidence, and future-story hint.

## Parent Status

- Status: Done
- Progress: Done
- Reason: Capability-gap capture, reset behavior, and unsupported-tool rejection are all covered by backend contract tests and the focused suite passed.

## Child Tasks

| Child task | Status | Evidence |
|---|---|---|
| BE-011.1 Verify unsupported capability produces typed gap/rejection | Done | `tests/test_capability_gaps.py::test_unknown_tool_records_gap_and_still_raises_runtime_error` |
| BE-011.2 Verify gap payload includes actionable reason/context | Done | `tests/test_capability_gaps.py::test_record_capability_gap_appends_ordinal` |
| BE-011.3 Verify unsupported work is not silently recorded or marked complete | Done | `tests/test_capability_gaps.py` and `agent.py` `_dispatch_tool` rejection path |
| BE-011.4 Verify gap handling does not mutate unrelated run state | Done | `tests/test_capability_gaps.py::test_reset_clears_capability_gaps` and backend isolation/reset tests |
| BE-011.5 Final capability gap audit | Done | Focused backend contract suite passed `59 passed` and confirmed the typed gap baseline remains stable |

### Done Children

- `BE-011.1` Verify unsupported capability produces typed gap/rejection
- `BE-011.2` Verify gap payload includes actionable reason/context
- `BE-011.3` Verify unsupported work is not silently recorded or marked complete
- `BE-011.4` Verify gap handling does not mutate unrelated run state
- `BE-011.5` Final capability gap audit

## Evidence

- `tests/test_capability_gaps.py` already covers recording, reset, and unsupported-tool rejection behavior.
- `agent.py` `_record_capability_gap` and `_dispatch_tool` provide the typed gap baseline.
- Focused backend contract suite passed `59 passed`.
- Branch status: branch-only on `dev1/backend-isolation-contract-tests`.

## Next Action

- None.

---

## Dependency map

| Dependency type | Items | Meaning |
|---|---|---|
| Upstream | SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001 | Planning rules and runtime state foundation |
| Direct blockers | advanced capability backlog, trace observability, unsupported action handling | Cannot proceed safely without this story or approved mocks |
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
| CapabilityGap | gap_id, run_id?, step_id?, operation_id?, needed_capability, current_tool_support, user_impact, recommended_followup?, evidence_ref?, status | required | gap truth |

---

## P0 persistence expectation

For P0, this story may use in-memory runtime structures unless existing repo architecture already has an accepted persistence path. The contract must remain structured enough for later session persistence, replay archive, trace, or saved-session work.

---

## Test matrix

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|
| BE011-U-001 | Unit | unsupported capability | upload op unsupported | gap recorded | no guessing |
| BE011-U-002 | Unit | gap missing capability | payload missing | rejected | schema |
| BE011-U-003 | Unit | LLM says possible | unsupported tool | gap still recorded | backend truth |
| BE011-I-001 | Integration | unsupported action flow | unsupported command/action | capability_gap_recorded | event contract |

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
