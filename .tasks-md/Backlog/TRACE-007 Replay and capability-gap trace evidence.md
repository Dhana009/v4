# TRACE-007 Replay and capability-gap trace evidence

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** TRACE-001, BE-011, BE-012, EVENT-008  
**Blocks:** replay smoke debugging, capability backlog, E2E evidence  
**Version:** Batch 10 v1  

---

## Product contribution

Traces replay attempts and unsupported capability gaps as audit evidence.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-012 | replay is backend operation, not frontend simulation | trace replay_started/result | replay evidence |
| EVENT-008 | replay has command/event contract | trace replay identity | replay correlation |
| BE-011 | capability gap is typed | trace gap id/capability | gap audit |
| SOURCE-001 | unsupported actionable gaps logged under workspace | trace gap evidence | future backlog |

---

## Architecture boundary

Replay/gap trace observes backend replay/gap events. It must not repair replay or mark unsupported capabilities as supported.

---

## Contract / schema

| Field | Required |
|---|---|
| replay_run_id | Conditional |
| replay_mode | Conditional |
| recorded_run_id/recorded_step_id/operation_id | Conditional |
| precondition_status | Conditional |
| replay_status | Conditional |
| gap_id | Conditional |
| needed_capability | Conditional |
| user_impact | Conditional |
| evidence_ref | Optional |
| diagnostics | Yes |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-001 | upstream | identity |
| BE-012 | upstream | replay status |
| BE-011 | upstream | gap status |
| TRACE-009 | downstream | export replay/gap evidence |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | traces replay/gap events |
| DEV-2 | may explain gap, no support hallucination |
| DEV-3 | displays replay/gap diagnostics |
| DEV-4 | asserts replay/gap artifacts |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE007-U-001 | Unit | replay_result trace | replay identity present |
| TRACE007-U-002 | Unit | wrong-page replay | precondition failure traced |
| TRACE007-U-003 | Unit | capability gap | gap trace present |
| TRACE007-I-001 | Integration | replay smoke | trace exported |

---

## Edge cases

- replay all partial failure
- missing archive
- unsupported iframe/upload
- repeated gap

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

First Codex task for TRACE-007 should be read-only:

```text
Read TRACE-007, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for Replay and capability-gap trace evidence.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
