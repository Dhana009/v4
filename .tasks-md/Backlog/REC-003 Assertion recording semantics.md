# REC-003 Assertion recording semantics

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-008 Recording and Codegen  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** REC-001, REC-002, DOM-006, BE-006  
**Blocks:** REC-004, MVP-003, MVP-004  
**Version:** Batch 09 v1  

---

## Product contribution

Protects assertion recording semantics, especially visible vs exact text assertions.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| DOM-006 | assertion target/value/metadata separate | recording must preserve separation | schema constraints |
| Handoff | exact text must not become visible assertion | codegen must reflect assertion type | tests |
| BE-006 | assertion operation must match confirmed plan | recording must use operation details | evidence mapping |
| SOURCE-001 | expected_outcome metadata only | never assertion target/value | reject leakage |

---

## Architecture boundary

Assertion recording records the executed assertion child exactly as validated by backend, not inferred from UI text or expected_outcome.

---

## Contract / schema

| Assertion type | Target required | Expected value required | Codegen impact |
|---|---|---|---|
| visible/hidden/enabled/disabled | yes | no | target-only assertion |
| checked/unchecked | yes | no | control assertion |
| has_text/contains_text | yes | yes | text contains |
| exact_text/text_equals | yes | yes | exact text |
| has_value | yes | yes | value assertion |
| url/title | page target | yes | page assertion |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| DOM-006 | upstream | assertion taxonomy |
| REC-001 | upstream | RecordedChild schema |
| REC-004 | downstream | codegen semantics |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | records assertion details |
| DEV-2 | planner must output explicit assertion type/value |
| DEV-3 | renders assertion metadata separately |
| DEV-4 | tests visible/exact text regressions |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC003-U-001 | Unit | visible assertion | no expected_value |
| REC003-U-002 | Unit | exact_text assertion | expected_value required |
| REC003-U-003 | Unit | expected_outcome leakage | rejected |
| REC003-U-004 | Unit | visible+has_text conflict | rejected/normalized |
| REC003-I-001 | Integration | exact code assertion recorded | correct child payload |

---

## Edge cases

- whitespace normalization
- duplicate text target
- code/pre target
- dynamic text

---

## Standard artifact/evidence expectation

| Artifact/evidence | Required | Notes |
|---|---|---|
| execution evidence ref | Yes where applicable | source action/assertion result |
| recorded step payload | Conditional | required for recording stories |
| code_update payload | Conditional | required for codegen stories |
| event stream excerpt | Conditional | required when event behavior changes |
| test output | Yes | unit/integration/E2E where applicable |
| diagnostics | Yes | structured errors/warnings |

---

## Required skills

Codex must load the smallest required skill pack only:

```text
.autoworkbench/skills/00_skill_usage_policy.md
.autoworkbench/skills/00_architecture_contract.md
.autoworkbench/skills/01_prd_scope_validation.md
.autoworkbench/skills/backend_step_runner.md
.autoworkbench/skills/typed_event_contract.md
.autoworkbench/skills/02_tdd_regression_harness.md
.autoworkbench/skills/03_refactor_safety.md
```

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current recording path and owner
- current `step_recorded` handling
- current successful action/assertion evidence model
- current expected_outcome and observed_outcome handling
- current code_update/codegen implementation
- current recorded step ordering/deduplication behavior
- current replay archive/persistence behavior
- existing tests covering recording/codegen
- source alignment gaps
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- recording would be built from LLM prose or `last_successful_action`
- codegen would run before backend recording is finalized
- expected_outcome would become assertion target/value
- recorded child order cannot be tied to confirmed execution contract
- frontend would own recorded/code truth
- replay archive semantics are unclear
- persistence path would require broad architecture changes
- tests cannot be written before implementation

---

## Codex execution summary

First Codex task for REC-003 should be read-only:

```text
Read REC-003, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Assertion recording semantics.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
