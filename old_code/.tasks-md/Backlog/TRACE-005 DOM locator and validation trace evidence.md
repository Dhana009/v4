# TRACE-005 DOM locator and validation trace evidence

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-009 Trace and Observability  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** TRACE-001, DOM-004, DOM-008, DOM-009  
**Blocks:** locator recovery debugging, E2E locator artifacts  
**Version:** Batch 10 v1  

---

## Product contribution

Traces DOM extraction, locator candidates, validation results, ambiguity routing, and update_locator decisions.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-004 | backend/browser validates final locator | trace captures validation result | locator evidence |
| DOM-004 | validation statuses are unique/multiple/none/stale/etc. | trace status/routing | ambiguity diagnosis |
| DOM-008 | specialist advisory only | trace suggestion vs validation | prevent LLM truth drift |
| DOM-009 | update_locator appends history | trace locator version/history | recovery audit |

---

## Architecture boundary

Locator trace is evidence. It cannot make a locator final or execute an action.

---

## Contract / schema

| Field | Required |
|---|---|
| candidate_id/locator_ref | Conditional |
| validation_status | Yes |
| match_count/visible_count | Conditional |
| ambiguity_candidates | Optional |
| route | Conditional | allow/recovery/clarification/capability_gap |
| specialist_used | Yes |
| update_locator_command_id | Conditional |
| locator_version_id | Conditional |
| evidence_ref | Optional |
| redacted_dom_summary | Optional |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-001 | upstream | identity |
| DOM-004 | upstream | validation result |
| DOM-009 | upstream | locator history |
| TRACE-008 | downstream | diagnostic UI |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | records validation evidence |
| DEV-2 | provides candidate/specialist trace, no final truth |
| DEV-3 | displays ambiguity/candidate diagnostics |
| DEV-4 | tests locator trace artifacts |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| TRACE005-U-001 | Unit | unique locator | trace validation unique |
| TRACE005-U-002 | Unit | multiple locator | ambiguity trace |
| TRACE005-U-003 | Unit | update_locator accepted | locator history traced |
| TRACE005-I-001 | Integration | duplicate CTA flow | no execution + trace |

---

## Edge cases

- huge DOM redaction
- hidden element
- iframe unsupported
- stale locator after navigation

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

First Codex task for TRACE-005 should be read-only:

```text
Read TRACE-005, SOURCE-001, PLAN-002, PLAN-005, EPIC-009, EPIC-001, EPIC-002, EPIC-006, EPIC-008, and required skills.
Do not edit code.
Inspect current trace/observability ownership for DOM locator and validation trace evidence.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
