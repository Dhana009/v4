# TRACE-002 Backend lifecycle event trace log

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** TRACE-001, EVENT-001, BE-001, BE-010  
**Blocks:** E2E event evidence, frontend diagnostics  
**Version:** Batch 10 v1  

---

## Product contribution

Captures backend lifecycle event evidence in a structured trace log.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-001 | backend owns lifecycle truth | trace observes backend state transitions | lifecycle trace records |
| EVENT-001 | canonical event envelope | trace records emitted event identity | event trace schema |
| BE-010 | run_completed only from completion guard | terminal event trace must be auditable | completion proof |
| EPIC-006 | E2E asserts event sequence | trace helps failure diagnosis | artifact export |

---

## Architecture boundary

Lifecycle trace observes emitted backend events. It must not create, suppress, or reinterpret lifecycle state.

---

## Contract / schema

Lifecycle trace record:

| Field | Required |
|---|---|
| trace_id/run_id | Yes |
| event_type | Yes |
| event_schema_version | Yes |
| lifecycle_state_before | Optional |
| lifecycle_state_after | Optional |
| payload_hash | Optional |
| event_ref/evidence_ref | Yes |
| emitted_at | Yes |
| diagnostic_summary | Optional |

Required event families:
`run_started`, `plan_ready`, `step_validating`, `step_executing`, `step_failed`, `step_recorded`, `code_update`, `run_completed`, `runtime_rejected`.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-001 | upstream | correlation model |
| EVENT-001 | upstream | event envelope |
| TRACE-009 | downstream | export event traces |
| E2E-002 | related | event capture assertions |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | emits/records lifecycle trace |
| DEV-2 | no mutation role |
| DEV-3 | renders diagnostic row only |
| DEV-4 | asserts sequence and artifacts |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE002-U-001 | Unit | run_started trace | recorded |
| TRACE002-U-002 | Unit | run_completed trace | terminal proof |
| TRACE002-U-003 | Unit | lifecycle trace mutates state | forbidden |
| TRACE002-I-001 | Integration | lifecycle event sequence | trace exported |

---

## Edge cases

- duplicate terminal event
- missing event payload
- event emitted during reconnect
- stale plan_version

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

First Codex task for TRACE-002 should be read-only:

```text
Read TRACE-002, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for Backend lifecycle event trace log.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
