# REC-001 Recorded step parent-child data model

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-008 Recording and Codegen  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** EPIC-008, BE-006, BE-009, EVENT-006  
**Blocks:** REC-002, REC-004, REC-006, REC-008, FE-006, E2E-010  
**Version:** Batch 09 v1  

---

## Product contribution

Defines the canonical data model for backend-owned recorded output.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-009 | parent recorded step with child operations/checks | model must be hierarchical | define RecordedStep and RecordedChild |
| BE-006 | confirmed plan children are contract | recorded IDs must trace to confirmed plan | include source IDs and version |
| EVENT-006 | step_recorded carries recorded parent/children | model must be event-compatible | schema maps to event payload |
| MVP-008 | multi-step order must be preserved | order indexes are required | include child order |

---

## Architecture boundary

Recording model is backend truth. Frontend renders it; LLM can explain it only.

---

## Contract / schema

### RecordedStep
| Field | Required | Meaning |
|---|---|---|
| recorded_step_id | Yes | recorded parent identity |
| run_id/plan_id/plan_version | Yes | traceability |
| source_step_id | Yes | original StepState |
| step_order_index | Yes | parent order |
| parent_intent | Yes | user-level intent |
| expected_outcome_metadata | Optional | metadata only |
| observed_outcome | Optional | observed summary |
| children | Yes | ordered RecordedChild list |
| status | Yes | recorded/skipped/failed |
| evidence_refs | Yes | execution/trace refs |

### RecordedChild
| Field | Required | Meaning |
|---|---|---|
| recorded_child_id | Yes | recorded child identity |
| operation_id/step_id | Yes | source operation/parent |
| child_order_index | Yes | confirmed child order |
| operation_type | Yes | click/fill/assert/navigate/etc. |
| locator_ref | Conditional | locator/action/assertion target |
| assertion_type/expected_value | Conditional | assertion details |
| result/evidence_ref | Yes | proof |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| BE-006 | upstream | confirmed contract IDs/order |
| BE-009 | upstream | recording owner |
| EVENT-006 | downstream | event payload |
| REC-004 | downstream | codegen consumes model |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | defines and validates model |
| DEV-2 | cannot mutate model; may consume for explanation |
| DEV-3 | renders model as-is |
| DEV-4 | asserts model shape/order |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC001-C-001 | Contract | valid RecordedStep | accepted |
| REC001-C-002 | Contract | missing source_step_id | rejected |
| REC001-C-003 | Contract | child missing operation_id | rejected |
| REC001-C-004 | Contract | duplicate child order | rejected |
| REC001-C-005 | Contract | expected_outcome as assertion value | rejected |

---

## Edge cases

- skipped step
- failed child
- optional child skipped
- multi-child step
- duplicate operation IDs

---

## Standard artifact/evidence expectation

| Artifact/evidence | Required | Notes |
|---|---|---|
| execution evidence ref | Yes where applicable | source action/assertion result |
| recorded step payload | Conditional | required for recording stories |
| code_update payload | Conditional | required for codegen stories |
| event stream excerpt | Conditional | required when event behavior changes |
| test output | Yes | unit/integration/E2E where applicable |
| diagnostics | Yes | structured errors/warnings |

---

## Required skills

Codex must load the smallest required skill pack only:

```text
.autoworkbench/skills/00_skill_usage_policy.md
.autoworkbench/skills/00_architecture_contract.md
.autoworkbench/skills/01_prd_scope_validation.md
.autoworkbench/skills/backend_step_runner.md
.autoworkbench/skills/typed_event_contract.md
.autoworkbench/skills/02_tdd_regression_harness.md
.autoworkbench/skills/03_refactor_safety.md
```

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current recording path and owner
- current `step_recorded` handling
- current successful action/assertion evidence model
- current expected_outcome and observed_outcome handling
- current code_update/codegen implementation
- current recorded step ordering/deduplication behavior
- current replay archive/persistence behavior
- existing tests covering recording/codegen
- source alignment gaps
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- recording would be built from LLM prose or `last_successful_action`
- codegen would run before backend recording is finalized
- expected_outcome would become assertion target/value
- recorded child order cannot be tied to confirmed execution contract
- frontend would own recorded/code truth
- replay archive semantics are unclear
- persistence path would require broad architecture changes
- tests cannot be written before implementation

---

## Codex execution summary

First Codex task for REC-001 should be read-only:

```text
Read REC-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Recorded step parent-child data model.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
