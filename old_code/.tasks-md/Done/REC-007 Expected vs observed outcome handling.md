# REC-007 Expected vs observed outcome handling

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
**Dependencies:** REC-001, REC-002, DOM-006, BE-009  
**Blocks:** trace/recording UI, assertion safety  
**Version:** Batch 09 v1  

---

## Product contribution

Defines how expected_outcome and observed_outcome appear in recording without corrupting assertions.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| Handoff | expected_outcome parent metadata only | keep metadata separate | schema/rules |
| BE-009 | observed_outcome basic capture exists | include observed summary | recording payload |
| DOM-006 | assertion target/value separate | no metadata leakage | validation |
| FE-006 | metadata display only | UI renders separately | event payload |

---

## Architecture boundary

expected_outcome and observed_outcome are metadata/evidence summaries, not locator targets, assertion values, or codegen sources.

---

## Contract / schema

| Field | Scope | Allowed use |
|---|---|---|
| expected_outcome_metadata | RecordedStep parent | display/summary only |
| observed_outcome.type | RecordedStep parent | evidence summary |
| observed_outcome.url/title before/after | parent evidence | trace/debug |
| observed_outcome.matched_expected | nullable summary | display only |
| assertion expected_value | RecordedChild | codegen assertion source |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-001 | upstream | metadata fields |
| DOM-006 | upstream | assertion separation |
| FE-006 | downstream | UI display |
| REC-004 | downstream | codegen safety |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | stores outcome metadata safely |
| DEV-2 | cannot infer assertion value from metadata |
| DEV-3 | displays metadata separately |
| DEV-4 | tests no leakage |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC007-U-001 | Unit | expected_outcome present | parent metadata only |
| REC007-U-002 | Unit | observed_outcome present | display/trace only |
| REC007-U-003 | Unit | expected_outcome as code value | rejected |
| REC007-I-001 | Integration | recorded payload UI | metadata separate |

---

## Edge cases

- expected_outcome contains exact text
- observed outcome null
- navigation observed
- no visible change

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

First Codex task for REC-007 should be read-only:

```text
Read REC-007, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Expected vs observed outcome handling.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
