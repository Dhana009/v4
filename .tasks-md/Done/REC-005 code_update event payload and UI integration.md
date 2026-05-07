# REC-005 code_update event payload and UI integration

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-008 Recording and Codegen  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** REC-004, EVENT-006, FE-006, BE-009  
**Blocks:** frontend code panel, E2E-010, MVP flows  
**Version:** Batch 09 v1  

---

## Product contribution

Defines when and how `code_update` is emitted and consumed.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EVENT-006 | code_update follows finalized recording | event payload required | define payload/rules |
| FE-006 | frontend renders backend code_update | UI is consumer only | UI integration |
| BE-009 | recording triggers codegen eligibility | no code before recording | enforce sequence |
| EPIC-006 | E2E asserts code_update artifacts | event payload saved | tests/artifacts |

---

## Architecture boundary

`code_update` is emitted by backend after recording/codegen; frontend does not generate or correct code truth.

---

## Contract / schema

| Field | Required | Meaning |
|---|---|---|
| type | Yes | code_update |
| run_id | Yes | run scope |
| step_id | Conditional | source step |
| source_recording_ids | Yes | recorded step(s) |
| lines | Yes unless diagnostic_only | code lines |
| diagnostics | Yes | warnings/errors |
| diagnostic_only | Yes | whether code lines absent |
| generated_at | Yes | timestamp |
| codegen_version | Yes | generator version |

| Situation | Required behavior |
|---|---|
| recording finalized | may emit code_update |
| recording incomplete | must not emit normal code_update |
| failed codegen | diagnostic/rejection, no fake code |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-004 | upstream | generated lines |
| EVENT-006 | upstream | event envelope |
| FE-006 | downstream | code panel |
| E2E-010 | downstream | event sequence tests |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | emits payload |
| DEV-2 | may review diagnostics only |
| DEV-3 | renders code/diagnostics |
| DEV-4 | asserts code_update after step_recorded |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC005-C-001 | Contract | valid code_update | accepted |
| REC005-C-002 | Contract | code_update before recording | rejected/no emit |
| REC005-C-003 | Contract | diagnostic_only no lines | accepted |
| REC005-I-001 | Integration | step_recorded then code_update | ordered events |
| REC005-I-002 | Integration | frontend panel render | code visible |

---

## Edge cases

- long code
- duplicate update
- failed codegen
- missing source recording

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

First Codex task for REC-005 should be read-only:

```text
Read REC-005, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for code_update event payload and UI integration.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
