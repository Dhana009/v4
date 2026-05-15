# MVP-008 Multi-step isolation and strict cursor flow

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, BE-006, BE-009, DOM-004, EVENT-005, E2E-008, E2E-009  
**Blocks:** multi-step V1 regression acceptance  
**Version:** Batch 08 v1  

---

## Product contribution

This story proves multiple steps execute in the confirmed order without cross-step contamination.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-006 | strict confirmed execution cursor | each operation must match expected step/child | assert cursor |
| Handoff | multi-step identity once mixed steps | regression must cover known bug | test 4-step flow |
| BE-009 | recording preserves confirmed child order | recorded UI/code must match execution | assert child order |
| EPIC-006 | E2E catches integration drift | full flow artifact required | E2E evidence |

## Required 4-step flow

```text
01 click Agents
02 assert Playwright Test Agents visible
03 click OpenCode/Claude Code tab
04 assert command text visible/exact
```

Equivalent local fixture may be used if Playwright.dev is captured locally.

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | enforces strict cursor and recording order |
| DEV-2 LLM/DOM | proposes multi-step plan with stable child identities |
| DEV-3 Frontend | renders ordered steps and recorded output |
| DEV-4 E2E | verifies no cross-step contamination |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP008-E-001 | E2E | four-step flow | all operations in order |
| MVP008-E-002 | E2E | wrong step operation | runtime_rejected |
| MVP008-E-003 | E2E | recorded order | matches confirmed plan |
| MVP008-E-004 | E2E | code order | matches recorded children |

## Edge cases

- same target text in different sections
- navigation/page state changes
- stale tool call from previous step
- assertion target from wrong section

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

First Codex task for MVP-008 should be read-only:

```text
Read MVP-008, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for Multi-step isolation and strict cursor flow.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
