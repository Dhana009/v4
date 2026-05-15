# TRACE-008 Frontend diagnostic trace panel contract

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** TRACE-001, FE-007, FE-009  
**Blocks:** Shadow DOM diagnostics UI, E2E UI assertions  
**Version:** Batch 10 v1  

---

## Product contribution

Defines the read-only frontend trace/diagnostic panel contract.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-005 | frontend renders backend truth only | trace panel cannot infer lifecycle | read-only panel |
| FE-007 | trace panel displays diagnostics | define panel contract | UI behavior |
| FE-009 | stable hooks/accessibility required | trace panel hooks | E2E selectors |
| TRACE-001 | trace correlation model | UI groups by IDs | display grouping |

---

## Architecture boundary

Trace panel is a diagnostic read-model. It must never set run/step/recording state.

---

## Contract / schema

Required panels/groups:

| Group | Examples |
|---|---|
| lifecycle | backend event traces |
| commands/rejections | command/rejection traces |
| LLM | telemetry/schema traces |
| DOM/locator | validation evidence |
| recording/codegen | recorded/code traces |
| replay/gaps | replay/gap traces |
| artifacts | evidence refs/export links |

Required hooks:
`aw-panel-trace`, `aw-trace-row`, `aw-trace-filter`, `aw-trace-export`, `aw-trace-redaction-warning`.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| FE-007 | upstream | trace UI behavior |
| FE-009 | upstream | hooks |
| TRACE-009 | downstream | export link |
| DEV-4 E2E | downstream | UI assertions |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | provides trace payloads |
| DEV-2 | provides LLM/DOM trace payloads |
| DEV-3 | owns read-only panel |
| DEV-4 | tests panel does not mutate state |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE008-U-001 | Unit | render lifecycle trace | row shown |
| TRACE008-U-002 | Unit | trace row clicked | no runtime mutation |
| TRACE008-U-003 | Unit | redaction warning | shown |
| TRACE008-I-001 | Integration | failure trace visible | diagnostic panel proof |

---

## Edge cases

- huge trace list
- missing evidence_ref
- redacted payload
- frontend reconnect

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

First Codex task for TRACE-008 should be read-only:

```text
Read TRACE-008, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for Frontend diagnostic trace panel contract.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
