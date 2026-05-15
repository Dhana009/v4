# MVP-006 Clarification before planning flow

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, LLM-005, EVENT-007, FE-005, BE-003, E2E-009  
**Blocks:** ambiguity/no-guessing acceptance  
**Version:** Batch 08 v1  

---

## Product contribution

This story proves the system asks for clarification instead of guessing when the user intent is ambiguous or missing required data.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| LLM-005 | low confidence/missing info routes clarification | no guessing | assert clarification_needed |
| EVENT-007 | clarification uses typed event/option_selected | frontend renders backend question | assert command shape |
| SOURCE-001 | human feedback preferred over guessing | block plan until resolved | no plan_ready early |
| EPIC-005 | UI cannot resolve truth locally | backend event drives state | assert UI behavior |

## Required flow

```text
ambiguous intent
→ intent classifier planner_ready=false
→ backend emits clarification_needed
→ UI renders question/options
→ user answers
→ backend resumes planning
→ plan_ready appears only after answer
```

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | owns clarification state and command validation |
| DEV-2 LLM | proposes clarification question/options |
| DEV-3 Frontend | renders clarification and sends option_selected |
| DEV-4 E2E | asserts no plan/execution before clarification resolved |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP006-E-001 | E2E | ambiguous target | clarification_needed |
| MVP006-E-002 | E2E | no early plan | no plan_ready before answer |
| MVP006-E-003 | E2E | answer clarification | option_selected command |
| MVP006-E-004 | E2E | plan after answer | plan_ready |

## Edge cases

- user gives irrelevant answer
- multiple possible targets
- low confidence medium policy
- stale clarification id

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

First Codex task for MVP-006 should be read-only:

```text
Read MVP-006, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for Clarification before planning flow.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
