# REC-008 Recording persistence and replay archive baseline

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
**Dependencies:** REC-001, REC-002, REC-005, BE-012, MVP-009  
**Blocks:** replay smoke, save/load baseline  
**Version:** Batch 09 v1  

---

## Product contribution

Defines the minimal persistence/archive shape required for replay smoke and future session restore.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-012 | replay uses recorded steps, not frontend simulation | archive recorded data | replay baseline |
| BE-001 | P0 persistence may be in-memory unless path exists | do not over-scope persistence | conditional storage |
| MVP-009 | save/load smoke conditional | support typed gap if unsupported | no hidden blocker |
| SOURCE-001 | storage defaults active workspace unless specified | no hardcoded hidden path | storage rule |

---

## Architecture boundary

P0 requires a replay/archive baseline or typed gap. It does not require full robust session restore unless repo inspection confirms supported path.

---

## Contract / schema

| Field | Required | Meaning |
|---|---|---|
| archive_id | Yes | archive identity |
| run_id | Yes | source run |
| recorded_steps | Yes | ordered recorded steps |
| code_updates | Optional | generated code |
| created_at | Yes | timestamp |
| storage_location | Conditional | path/ref |
| replay_eligible | Yes | true/false |
| diagnostics | Yes | warnings/gaps |

| Repo state | Required behavior |
|---|---|
| persistence exists | use source-aligned path |
| no persistence | in-memory archive for P0 smoke or typed gap |
| unclear path | stop and report |
| save/load unsupported | typed gap, not silent fail |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-001 | upstream | recorded data |
| BE-012 | downstream | replay consumes archive |
| MVP-009 | related | session smoke |
| E2E-010 | downstream | replay artifact tests |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | owns archive/persistence baseline |
| DEV-2 | no role except explanation |
| DEV-3 | renders replay eligibility if needed |
| DEV-4 | tests replay archive smoke |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC008-U-001 | Unit | archive from recorded steps | valid archive |
| REC008-U-002 | Unit | missing recorded children | not replay eligible |
| REC008-U-003 | Unit | unsupported persistence | typed gap |
| REC008-I-001 | Integration | replay smoke source | archive consumed |

---

## Edge cases

- partial recorded run
- stale archive
- missing code_update
- active workspace unavailable

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

First Codex task for REC-008 should be read-only:

```text
Read REC-008, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Recording persistence and replay archive baseline.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
