# TRACE-010 Observability regression and redaction policy

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** TRACE-001, TRACE-009, PLAN-005  
**Blocks:** release safety, privacy, regression guard  
**Version:** Batch 10 v1  

---

## Product contribution

Defines regression tests and redaction rules for observability so traces are useful and safe.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| PLAN-005 | tests prove acceptance | observability needs regression tests | test matrix |
| SOURCE-001 | capability gaps logged safely | logs must be actionable and safe | redaction policy |
| EPIC-009 | sensitive values require redaction | define rules | safety |
| MVP-010 | release gate checks artifacts | redaction/artifact checks gate | acceptance |

---

## Architecture boundary

Observability tests verify evidence quality and privacy. They must not depend on or change runtime truth.

---

## Contract / schema

Redaction policy:

| Data type | Default |
|---|---|
| passwords/tokens/API keys | redact |
| OTP/email auth codes | redact |
| personal contact data | redact/mask |
| resumes/private uploads | do not log raw content |
| long user text | summarize or hash when possible |
| locators/URLs | allowed unless sensitive |
| generated code | allowed unless contains secret/user data |

Regression requirements:
- every failed E2E flow produces artifact bundle
- trace records have correlation IDs
- no forbidden sensitive patterns in exported logs
- frontend trace panel remains read-only
- free-form logs are not the only evidence

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-001 | upstream | correlation IDs |
| TRACE-009 | upstream | export layout |
| PLAN-005 | upstream | test strategy |
| MVP-010 | downstream | release gate |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | marks backend sensitive fields |
| DEV-2 | redacts LLM prompts/outputs where needed |
| DEV-3 | does not expose raw sensitive trace in UI |
| DEV-4 | owns redaction regression checks |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE010-U-001 | Unit | token-like value | redacted |
| TRACE010-U-002 | Unit | missing correlation ID | test fails |
| TRACE010-U-003 | Unit | frontend trace mutation attempt | forbidden |
| TRACE010-I-001 | Integration | failed flow artifacts | redaction report passes |
| TRACE010-G-001 | Gate | artifact missing/redaction fail | release gate fails |

---

## Edge cases

- false-positive redaction
- redaction hides useful evidence
- binary artifacts
- local-only logs
- user-provided sensitive text

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

First Codex task for TRACE-010 should be read-only:

```text
Read TRACE-010, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for Observability regression and redaction policy.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
