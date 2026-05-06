# REC-004 Deterministic Playwright codegen from recorded children

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-008 Recording and Codegen  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** REC-001, REC-002, REC-003, DOM-003, DOM-006  
**Blocks:** REC-005, FE-006, E2E-010  
**Version:** Batch 09 v1  

---

## Product contribution

Generates deterministic Playwright code from recorded children.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| SOURCE-001 | codegen deterministic and backend-owned first | no LLM code truth | deterministic generator |
| REC-001 | recorded children have ordered operation data | codegen consumes recorded model | map operations to code lines |
| DOM-003 | semantic locator ranking | codegen should use validated locator | preserve Playwright locator |
| DOM-006 | assertion taxonomy | codegen assertion correctly | map assertion types |

---

## Architecture boundary

Codegen takes RecordedStep/RecordedChild as input. It must not regenerate from LLM plan or frontend state.

---

## Contract / schema

| Operation | Codegen baseline |
|---|---|
| click | `await locator.click();` |
| fill | `await locator.fill(value);` |
| select | `await locator.selectOption(value);` |
| check/uncheck | `await locator.check()/uncheck();` |
| visible assertion | `await expect(locator).toBeVisible();` |
| hidden assertion | `await expect(locator).toBeHidden();` |
| exact_text | `await expect(locator).toHaveText(value);` |
| contains_text | `await expect(locator).toContainText(value);` |
| has_value | `await expect(locator).toHaveValue(value);` |
| navigation/url/title | page-level expect/navigation |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-001 | upstream | codegen input |
| REC-003 | upstream | assertion semantics |
| REC-005 | downstream | code_update payload |
| REC-009 | downstream | diagnostics/review |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | owns deterministic generator |
| DEV-2 | optional reviewer only, no code truth |
| DEV-3 | renders generated lines |
| DEV-4 | compares code to recorded evidence |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC004-U-001 | Unit | click child | click line |
| REC004-U-002 | Unit | fill child | fill line with value |
| REC004-U-003 | Unit | visible assertion | toBeVisible |
| REC004-U-004 | Unit | exact_text assertion | toHaveText |
| REC004-U-005 | Unit | unsupported operation | diagnostic/gap |

---

## Edge cases

- quote escaping
- multi-line text
- generated locator unavailable
- unsupported operation type
- code order mismatch

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

First Codex task for REC-004 should be read-only:

```text
Read REC-004, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Deterministic Playwright codegen from recorded children.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
