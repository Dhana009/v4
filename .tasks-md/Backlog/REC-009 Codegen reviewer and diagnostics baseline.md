# REC-009 Codegen reviewer and diagnostics baseline

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-008 Recording and Codegen  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** REC-004, REC-005, LLM-010  
**Blocks:** diagnostics, future code quality review  
**Version:** Batch 09 v1  

---

## Product contribution

Defines an advisory diagnostics/reviewer layer for generated code quality without making LLM the codegen source of truth.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| SOURCE-001 | LLM can suggest but backend owns truth | reviewer cannot mutate code truth | advisory-only diagnostics |
| REC-004 | deterministic generator owns code lines | reviewer consumes output | diagnostics only |
| LLM-010 | telemetry/cost guard | review calls must be observable | telemetry required |
| EVENT-006 | diagnostics can travel in code_update | attach warnings/errors | payload integration |

---

## Architecture boundary

Reviewer/diagnostics may flag issues, risk, unsupported operations, or formatting suggestions. It must not replace backend-generated code unless a future backend-validated story allows it.

---

## Contract / schema

| Diagnostic | Meaning |
|---|---|
| unsupported_operation | codegen cannot produce line |
| brittle_locator | locator risk warning |
| missing_evidence | recorded child lacks proof |
| assertion_semantics_risk | target/value ambiguity |
| formatting_warning | non-blocking style issue |
| reviewer_suggestion | advisory only |

| Field | Required |
|---|---|
| diagnostic_code | Yes |
| severity | info/warning/error |
| message | Yes |
| source_recording_id | Conditional |
| source_child_id | Conditional |
| reviewer | deterministic/LLM/manual |
| applied_to_code | always false for P0 reviewer suggestions |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-004 | upstream | generated code |
| REC-005 | downstream | code_update diagnostics |
| LLM-010 | related | telemetry if LLM used |
| REC-010 | downstream | diagnostic tests |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | owns diagnostic generation and application policy |
| DEV-2 | may provide advisory review with telemetry |
| DEV-3 | renders diagnostics separately from code truth |
| DEV-4 | tests diagnostics do not mutate code |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC009-U-001 | Unit | unsupported op | diagnostic emitted |
| REC009-U-002 | Unit | LLM reviewer suggestion | not applied automatically |
| REC009-U-003 | Unit | brittle locator warning | warning diagnostic |
| REC009-I-001 | Integration | diagnostics in code_update | UI renders separately |

---

## Edge cases

- reviewer unavailable
- high-cost review skipped
- false-positive warning
- diagnostic-only code_update

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

First Codex task for REC-009 should be read-only:

```text
Read REC-009, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Codegen reviewer and diagnostics baseline.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
