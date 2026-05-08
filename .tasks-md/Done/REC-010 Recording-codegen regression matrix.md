# REC-010 Recording-codegen regression matrix

Status: Done  
Sprint: Sprint 0  


**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-008 Recording and Codegen  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** REC-001, REC-002, REC-003, REC-004, REC-005, REC-006, E2E-010, MVP-010  
**Blocks:** release evidence and regression guard  
**Version:** Batch 09 v1  

---

## Product contribution

Defines the regression matrix proving recording and codegen are safe before release.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| PLAN-005 | no story done without test evidence | regression matrix required | acceptance proof |
| MVP-010 | gate needs recording/code evidence | tests feed release gate | required flows |
| E2E-010 | recording/code_update/replay smoke | integrate product E2E | artifact expectations |
| Handoff | exact text, correction, multi-step were known risks | matrix covers known regressions | blocker tests |

---

## Architecture boundary

Regression matrix is an acceptance layer. It should not implement features; it defines required proof across unit, integration, and E2E.

---

## Contract / schema

Required coverage:

| Flow | Required proof |
|---|---|
| simple click | recorded click child + click code |
| visible assertion | assertion child + toBeVisible code |
| exact text/code assertion | exact expected value + exact text code |
| fill/select | input value recorded + code |
| correction assert-then-click | revised child order |
| multi-step strict cursor | recorded/code order matches contract |
| failed child | no recorded parent/no code_update |
| expected_outcome metadata | no target/value leakage |
| code_update sequence | after step_recorded |
| replay smoke | archive consumed or typed gap |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-001..REC-006 | upstream | feature behavior |
| E2E-010 | upstream | E2E harness flow |
| MVP-010 | downstream | release gate |
| EPIC-006 | related | artifact model |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | provides backend/unit/integration evidence |
| DEV-2 | provides mocked LLM outputs where needed |
| DEV-3 | verifies recorded/code UI |
| DEV-4 | owns E2E matrix artifacts |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC010-R-001 | Regression | click recording/code | pass |
| REC010-R-002 | Regression | visible assertion | pass |
| REC010-R-003 | Regression | exact text assertion | pass |
| REC010-R-004 | Regression | correction order | pass |
| REC010-R-005 | Regression | failed child no code_update | pass |
| REC010-R-006 | Regression | replay smoke | pass or typed gap |

---

## Edge cases

- flaky LLM output
- missing artifact
- codegen diagnostic warning
- non-MVP unsupported operation

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

First Codex task for REC-010 should be read-only:

```text
Read REC-010, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Recording-codegen regression matrix.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
