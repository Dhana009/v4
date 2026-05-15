# TRACE-003 Command and rejection trace log

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** TRACE-001, EVENT-002, EVENT-003, BE-003  
**Blocks:** debug command failures, frontend rejection UI, E2E negative flows  
**Version:** Batch 10 v1  

---

## Product contribution

Traces frontend/backend commands and typed rejections so invalid actions are debuggable.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EVENT-002 | commands use canonical envelope | trace command_id/type/payload summary | command trace |
| EVENT-003 | rejections are structured | trace rejection code/current state | rejection trace |
| BE-003 | backend validates commands | trace validation result | command debugging |
| EPIC-005 | UI sends commands only | trace frontend command source | frontend command audit |

---

## Architecture boundary

Command trace records request/validation/rejection evidence only. It must not retry or mutate command outcomes.

---

## Contract / schema

| Field | Required | Meaning |
|---|---|---|
| command_id | Yes | command correlation |
| command_type | Yes | canonical command |
| source | Yes | frontend/user/system |
| validation_status | Yes | accepted/rejected |
| rejection_code | Conditional | if rejected |
| current_state_summary | Optional | state at rejection |
| payload_redacted | Yes | safe payload summary |
| linked_event_ref | Optional | event/rejection emitted |
| run_id/plan_id/step_id | Conditional | scope |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-001 | upstream | IDs |
| EVENT-002 | upstream | command envelope |
| EVENT-003 | upstream | rejection payload |
| TRACE-008 | downstream | diagnostics UI |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | validates and traces command outcome |
| DEV-2 | no direct command truth |
| DEV-3 | sends commands and renders rejection trace |
| DEV-4 | tests command/rejection trace |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE003-U-001 | Unit | accepted command | trace accepted |
| TRACE003-U-002 | Unit | rejected stale confirm | STALE_PLAN_VERSION traced |
| TRACE003-U-003 | Unit | sensitive command payload | redacted |
| TRACE003-I-001 | Integration | UI command rejected | trace + UI diagnostic |

---

## Edge cases

- duplicate command_id
- disconnected command
- malformed command
- rejection without command_id

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

First Codex task for TRACE-003 should be read-only:

```text
Read TRACE-003, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for Command and rejection trace log.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
