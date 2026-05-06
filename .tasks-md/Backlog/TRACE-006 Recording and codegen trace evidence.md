# TRACE-006 Recording and codegen trace evidence

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** TRACE-001, REC-001, REC-005, REC-009  
**Blocks:** recording/code debug, E2E artifacts, frontend diagnostics  
**Version:** Batch 10 v1  

---

## Product contribution

Traces how execution evidence becomes recorded steps and code_update diagnostics.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-008 | recording/codegen backend-owned | trace links evidence to recorded/code output | recording trace |
| REC-001 | recorded model has parent/child IDs | trace recorded_step_id/child IDs | correlation |
| REC-005 | code_update has source_recording_ids/codegen_version | trace codegen output | code trace |
| REC-009 | diagnostics advisory-only | trace diagnostics without mutation | reviewer boundary |

---

## Architecture boundary

Recording/codegen trace observes the builder and generator. It must not alter recorded payloads or generated code.

---

## Contract / schema

| Field | Required |
|---|---|
| recorded_step_id | Conditional |
| recorded_child_ids | Conditional |
| source_step_id | Conditional |
| source_operation_ids | Conditional |
| codegen_version | Conditional |
| source_recording_ids | Conditional |
| diagnostic_codes | Optional |
| code_update_ref | Conditional |
| evidence_refs | Yes where available |
| emitted_after_step_recorded | Conditional | sequence proof |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-001 | upstream | identity |
| REC-001 | upstream | recorded IDs |
| REC-005 | upstream | code_update payload |
| TRACE-009 | downstream | artifact export |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | traces recording/codegen path |
| DEV-2 | traces advisory review only |
| DEV-3 | renders diagnostics read-only |
| DEV-4 | asserts recording/code trace |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE006-U-001 | Unit | step_recorded trace | recorded IDs linked |
| TRACE006-U-002 | Unit | code_update trace | source_recording_ids linked |
| TRACE006-U-003 | Unit | diagnostic suggestion | not applied as code truth |
| TRACE006-I-001 | Integration | recording to code_update | trace sequence exported |

---

## Edge cases

- code_update before recording
- missing recorded child
- diagnostic-only update
- unsupported codegen operation

---

## Standard artifact/evidence expectation

| Artifact/evidence | Required | Notes |
|---|---|---|
| trace record payload | Yes | canonical trace evidence for this story |
| event stream excerpt | Conditional | required if event source touched |
| command/rejection excerpt | Conditional | required if command path touched |
| telemetry excerpt | Conditional | required if LLM path touched |
| screenshot/DOM/evidence ref | Conditional | required if browser/DOM path touched |
| test output | Yes | unit/integration/E2E where applicable |
| redaction check | Yes | no sensitive leakage |

---

## Required skills

Codex must load the smallest required skill pack only:

```text
.autoworkbench/skills/00_skill_usage_policy.md
.autoworkbench/skills/00_architecture_contract.md
.autoworkbench/skills/01_prd_scope_validation.md
.autoworkbench/skills/typed_event_contract.md
.autoworkbench/skills/02_tdd_regression_harness.md
.autoworkbench/skills/03_refactor_safety.md
```

Add backend, frontend, LLM, DOM/locator, or E2E-specific skills only when the story touches those areas.

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current logging/trace files and owners
- current event, command, telemetry, DOM, recording, replay, and artifact evidence paths
- current correlation IDs available
- current redaction/sensitive-data behavior
- current frontend trace/diagnostic UI behavior
- current artifact bundle/export behavior
- existing tests covering observability
- source alignment gaps
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- trace would become runtime source of truth
- trace modifies backend/frontend state instead of observing it
- sensitive data redaction policy is unclear
- correlation IDs cannot link event/command/recording evidence
- logs are free-form only and cannot be asserted
- frontend trace panel would infer lifecycle state
- artifact export includes private/sensitive data without policy
- implementation requires broad rewrite before tests

---

## Codex execution summary

First Codex task for TRACE-006 should be read-only:

```text
Read TRACE-006, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for Recording and codegen trace evidence.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
