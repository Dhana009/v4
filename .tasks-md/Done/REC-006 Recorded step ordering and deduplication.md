# REC-006 Recorded step ordering and deduplication

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-008 Recording and Codegen  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** REC-001, REC-002, BE-006, MVP-008  
**Blocks:** multi-step stability, REC-004, REC-010  
**Version:** Batch 09 v1  

---

## Product contribution

Protects recorded UI/code order and prevents duplicate/misaligned recorded children.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-006 | strict cursor and confirmed child order | recording must preserve order | order checks |
| Handoff | recorded steps must preserve identity/order | stable display/code order | identity/dedup rules |
| MVP-008 | multi-step isolation required | order regressions are blockers | tests |

---

## Architecture boundary

Ordering/deduplication is backend-owned. Frontend may sort for display only using backend order fields and IDs.

---

## Contract / schema

| Item | Rule |
|---|---|
| recorded_step order | confirmed step_order_index |
| child order | confirmed child_order_index |
| duplicate recorded_step_id | idempotent update or reject by policy |
| duplicate operation_id in same step | reject |
| stale plan version | reject |
| frontend sort fallback | display-only, no truth mutation |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-001 | upstream | order fields |
| BE-006 | upstream | confirmed order |
| REC-004 | downstream | code order |
| REC-010 | downstream | regression matrix |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | enforces backend order/dedup |
| DEV-2 | preserves identities in plan outputs |
| DEV-3 | renders backend order |
| DEV-4 | tests multi-step order |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC006-U-001 | Unit | children out of order | rejected/reordered by policy |
| REC006-U-002 | Unit | duplicate operation_id | rejected |
| REC006-U-003 | Unit | duplicate step_recorded | idempotent/reject |
| REC006-I-001 | Integration | four-step flow recording | order preserved |
| REC006-I-002 | Integration | code order | matches recorded children |

---

## Edge cases

- retried operation
- skipped step
- correction changed order
- replay archive order

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

First Codex task for REC-006 should be read-only:

```text
Read REC-006, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Recorded step ordering and deduplication.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
