# TRACE-009 Artifact bundle and export format

**Type:** Story  
**Status:** Planned  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** TRACE-001, EPIC-006, E2E-010  
**Blocks:** E2E artifacts, handoff, release gate  
**Version:** Batch 10 v1  

---

## Product contribution

Defines the artifact/export format for trace evidence and regression runs.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-006 | E2E artifact bundles required | export must be deterministic | artifact schema |
| MVP-010 | release gate needs evidence | export feeds gate | report format |
| TRACE-001 | trace correlation model | export preserves IDs | searchable evidence |
| TRACE-010 | redaction policy required | export must include redaction report | safety |

---

## Architecture boundary

Artifact export is evidence. Exporting artifacts must not alter runtime state or test outcomes.

---

## Contract / schema

Suggested layout:

```text
artifacts/e2e/<timestamp>-<test_id>-<slug>/
  trace.ndjson
  events.ndjson
  commands.json
  rejections.json
  llm-telemetry.json
  locator-validation.json
  recording-codegen.json
  replay-gap.json
  frontend-diagnostics.json
  screenshots/
  traces/
  redaction-report.json
  summary.md
  test-result.json
```

Required summary fields:
test_id, run_id, status, failed_step, key event sequence, artifact files, redaction status, open gaps.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-001 | upstream | IDs |
| EPIC-006 | upstream | artifact model |
| TRACE-010 | upstream/downstream | redaction report |
| MVP-010 | downstream | release gate evidence |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | contributes backend/event logs |
| DEV-2 | contributes LLM/DOM evidence |
| DEV-3 | contributes frontend diagnostics |
| DEV-4 | owns export and assertions |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE009-U-001 | Unit | export layout | required files present |
| TRACE009-U-002 | Unit | missing trace file | export fails or warns |
| TRACE009-U-003 | Unit | redaction report | present |
| TRACE009-I-001 | Integration | failed E2E run | artifact bundle exported |

---

## Codex task breakdown

| Task | Status | Notes |
|---|---|---|
| TRACE-009A | Done | Completed mapping of current artifact writers and summary/manifest/result fields for event, command, and rejection evidence. |
| TRACE-009B | Done | Implemented `events.ndjson` emission baseline; tests/test_e2e_harness.py passes 22/22. |
| TRACE-009C | Done | Implemented `commands.json` emission baseline; tests/test_e2e_harness.py passes 25/25. |
| TRACE-009D | Done | Implemented `rejections.json` emission baseline; tests/test_e2e_harness.py passes 28/28. |
| TRACE-009E | Done | Verified consolidated events, commands, and rejections artifact emission; tests/test_e2e_harness.py passes 30/30. |
| TRACE-009F | Planned | Verify focused tests and record evidence. |

## Edge cases

- partial export
- large screenshots/traces
- missing optional files
- path collision

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

First Codex task for TRACE-009 should be read-only:

```text
Read TRACE-009, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for Artifact bundle and export format.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
