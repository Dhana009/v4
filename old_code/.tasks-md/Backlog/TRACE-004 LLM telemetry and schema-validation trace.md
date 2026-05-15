# TRACE-004 LLM telemetry and schema-validation trace

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** TRACE-001, LLM-001, LLM-004, LLM-010  
**Blocks:** LLM debugging, cost/token evidence, schema failure diagnosis  
**Version:** Batch 10 v1  

---

## Product contribution

Traces every controlled LLM call, schema validation, retry behavior, and backend validator outcome.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-003 | every LLM call has purpose/schema/tools/validator | trace must include purpose policy | LLM trace schema |
| LLM-004 | invalid schema retries once then fails closed | trace validation/retry status | schema trace |
| LLM-010 | telemetry includes model/tokens/latency | trace captures cost/performance | telemetry export |
| SOURCE-001 | LLM proposes only | trace cannot become runtime truth | advisory trace |

---

## Architecture boundary

LLM trace explains model behavior. It must not make LLM output accepted; backend/schema validators decide acceptance.

---

## Contract / schema

| Field | Required |
|---|---|
| llm_call_id | Yes |
| purpose | Yes |
| model | Yes |
| schema_id/version | Conditional |
| retry_count | Yes |
| validation_status | valid/invalid/retry_failed/backend_rejected |
| backend_validator | Conditional |
| estimated_input_tokens/estimated_output_tokens | Yes/Optional |
| latency_ms | Yes |
| skills_loaded | Yes |
| tools_exposed_count | Yes |
| error_code | Optional |
| output_ref_redacted | Optional |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-001 | upstream | trace identity |
| LLM-004 | upstream | validation state |
| LLM-010 | upstream | telemetry units |
| TRACE-009 | downstream | export telemetry |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | receives backend validator outcome |
| DEV-2 | owns LLM telemetry semantics |
| DEV-3 | displays trace only |
| DEV-4 | asserts retry/fail-closed evidence |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE004-U-001 | Unit | valid LLM call | telemetry trace |
| TRACE004-U-002 | Unit | invalid once then valid | retry_count=1 |
| TRACE004-U-003 | Unit | invalid twice | retry_failed |
| TRACE004-U-004 | Unit | backend rejection | backend_rejected |
| TRACE004-I-001 | Integration | plan diff invalid | trace shows no mutation |

---

## Edge cases

- local model missing token estimate
- streamed response
- redacted raw output
- telemetry logging failure

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

First Codex task for TRACE-004 should be read-only:

```text
Read TRACE-004, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for LLM telemetry and schema-validation trace.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
