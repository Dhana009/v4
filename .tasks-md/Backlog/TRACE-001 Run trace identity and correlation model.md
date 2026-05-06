# TRACE-001 Run trace identity and correlation model

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-009, EVENT-001, EVENT-002, REC-001  
**Blocks:** all TRACE stories, E2E artifact export  
**Version:** Batch 10 v1  

---

## Product contribution

Defines the shared trace identity model that connects events, commands, LLM calls, DOM evidence, recording/codegen, replay, and artifacts.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-002 | events/commands carry IDs | trace must correlate typed IDs | define correlation schema |
| EPIC-008 | recording/codegen has recorded_step_id/codegen_version | trace links output evidence | include recorded/code IDs |
| EPIC-006 | artifact bundles need evidence | trace_id links files | export-compatible model |
| SOURCE-001 | backend truth only | trace is evidence, not state | read-only model |

---

## Architecture boundary

Trace identity is a correlation read-model. It must not decide or mutate runtime status.

---

## Contract / schema

| Field | Required | Meaning |
|---|---|---|
| trace_id | Yes | trace record identity |
| run_id | Yes where run-scoped | primary correlation |
| command_id | Conditional | command/rejection link |
| plan_id/plan_version | Conditional | plan scope |
| step_id/operation_id | Conditional | execution scope |
| recorded_step_id/recorded_child_id | Conditional | recording scope |
| replay_run_id | Conditional | replay scope |
| llm_call_id | Conditional | LLM telemetry scope |
| evidence_ref | Optional | artifact pointer |
| emitted_at | Yes | trace timestamp |
| source | Yes | subsystem |
| trace_kind | Yes | lifecycle/command/llm/dom/recording/replay/frontend |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| EVENT-001 | upstream | event IDs |
| EVENT-002 | upstream | command IDs |
| REC-001 | upstream | recorded IDs |
| TRACE-009 | downstream | export uses correlation |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | defines backend correlation IDs |
| DEV-2 | maps llm_call_id into trace |
| DEV-3 | displays trace IDs read-only |
| DEV-4 | asserts correlation in artifacts |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE001-C-001 | Contract | valid trace identity | accepted |
| TRACE001-C-002 | Contract | missing run_id for run trace | rejected |
| TRACE001-C-003 | Contract | recording trace with recorded_step_id | accepted |
| TRACE001-U-001 | Unit | correlate command to rejection | linked by command_id |

---

## Edge cases

- trace without run scope
- replay traces referencing source run
- duplicate trace_id
- missing optional evidence_ref

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

First Codex task for TRACE-001 should be read-only:

```text
Read TRACE-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for Run trace identity and correlation model.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
