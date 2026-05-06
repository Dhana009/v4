# MVP-004 Exact text-code assertion flow

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, MVP-001, DOM-006, DOM-010, BE-006, BE-009, EVENT-006, E2E-005, E2E-008  
**Blocks:** exact text/code assertion acceptance  
**Version:** Batch 08 v1  

---

## Product contribution

This story validates exact text/code assertion semantics, one of the highest-risk known V1 flows.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| DOM-006 | exact_text requires explicit expected value and target | separate target/value | assert taxonomy |
| Handoff | exact text assertion must not become visible assertion | protect assertion semantics | verify code_update |
| DOM-010/E2E-005 | docs/code fixture needed | use code block fixture | fixture dependency |
| BE-009 | recording preserves child assertion | assert recorded child details | recording evidence |

## Required flow

```text
intent: assert exact command text in code block
→ plan_ready with exact_text assertion
→ confirm
→ text_block/code/pre target selected
→ exact expected value from user intent
→ assertion executes
→ code_update uses exact text assertion, not visible-only assertion
```

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | validates assertion type/value and recording |
| DEV-2 LLM/DOM | proposes exact_text assertion with explicit expected value |
| DEV-3 Frontend | renders recorded assertion/code accurately |
| DEV-4 E2E | uses docs-style fixture and asserts target/value separation |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP004-E-001 | E2E | exact code text | assertion passes |
| MVP004-E-002 | E2E | not visible-only | exact text code generated |
| MVP004-E-003 | E2E | expected_outcome not used | no metadata leakage |
| MVP004-E-004 | E2E | whitespace policy | explicit behavior |

## Edge cases

- code block whitespace
- duplicate command text
- line wrapping
- user gives partial text

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

Add frontend, LLM, DOM/locator, or E2E-specific skills only when this story touches those areas.

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current product flow for this scenario
- current backend lifecycle/event/command support
- current LLM runtime/schema support
- current DOM/locator support
- current Shadow DOM/frontend support
- current E2E/harness/fixture support
- existing tests covering this scenario
- source alignment gaps
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- scenario cannot be mapped to backend-owned truth
- frontend would need to infer lifecycle state
- LLM would own plan/execution/recording/completion truth
- event/command payloads are missing required IDs
- locator validation boundary is unclear
- E2E evidence cannot prove backend event + UI state
- implementation requires broad rewrite before tests
- scenario depends on live external site or nondeterministic LLM output as hard requirement

---

## Codex execution summary

First Codex task for MVP-004 should be read-only:

```text
Read MVP-004, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for Exact text-code assertion flow.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
