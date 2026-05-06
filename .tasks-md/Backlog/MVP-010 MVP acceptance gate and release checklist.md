# MVP-010 MVP acceptance gate and release checklist

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, MVP-001, MVP-002, MVP-003, MVP-004, MVP-005, MVP-006, MVP-007, MVP-008, MVP-009, E2E-010  
**Blocks:** release readiness decision  
**Version:** Batch 08 v1  

---

## Product contribution

This story defines the final gate for saying Complete LLM Mode MVP is stable enough to move beyond planning/stabilization.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| PLAN-005 | no story done without test evidence | MVP gate requires evidence bundle | checklist |
| Handoff | do not trust tests alone; run manual/live regression | include manual checklist | release evidence |
| EPIC-006 | artifact evidence required | gate uses artifacts | objective acceptance |
| SOURCE-001 | architecture boundaries are non-negotiable | gate checks no truth drift | architecture audit |

## Acceptance gate checklist

| Area | Required evidence |
|---|---|
| backend truth | lifecycle/recording/completion events |
| event/command contract | canonical payloads and rejections |
| LLM controller | mocked/validated outputs; no truth mutation |
| DOM/locator | validation/ambiguity evidence |
| frontend | Shadow DOM UI state through hooks |
| E2E | passing MVP flows and artifacts |
| recording/code | step_recorded and code_update validated |
| replay smoke | pass or clear P1 gap if not MVP blocker |
| known regressions | exact text, correction, multi-step covered |
| open gaps | documented as P1/P2/capability gaps |

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | signs off backend/event/recording evidence |
| DEV-2 LLM/DOM | signs off LLM/locator boundaries |
| DEV-3 Frontend | signs off Shadow DOM UI evidence |
| DEV-4 E2E | owns final regression report |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP010-G-001 | Gate | all MVP E2E passed | pass |
| MVP010-G-002 | Gate | missing artifact | fail gate |
| MVP010-G-003 | Gate | architecture drift found | fail gate |
| MVP010-G-004 | Gate | known V1 regression uncovered | fail gate |

## Final report format

```text
MVP status: pass/fail
commit/build id:
test commands:
passed flows:
failed flows:
artifact links/paths:
architecture drift checks:
open gaps:
release recommendation:
```

## Edge cases

- tests pass but artifacts missing
- replay smoke flaky
- manual regression uncovers issue
- non-MVP gap confused as blocker

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

First Codex task for MVP-010 should be read-only:

```text
Read MVP-010, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for MVP acceptance gate and release checklist.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
