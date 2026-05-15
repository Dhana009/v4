# MVP-007 Locator ambiguity and recovery flow

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, DOM-004, DOM-008, DOM-009, BE-008, EVENT-007, FE-005, FE-008, E2E-006, E2E-007, E2E-009  
**Blocks:** locator recovery acceptance  
**Version:** Batch 08 v1  

---

## Product contribution

This story proves ambiguous/missing/stale locators do not execute blindly and route to recovery/clarification/update_locator.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| DOM-004 | validation classifies multiple/none/stale/hidden/wrong_page | ambiguity explicit | assert validation route |
| DOM-008 | specialist advisory only | LLM cannot own locator truth | assert backend validation |
| DOM-009 | update_locator command backend-validated | user candidate does not mutate truth | assert update flow |
| BE-008 | recovery blocks completion | failed locator opens recovery | no run_completed |

## Required flow

```text
ambiguous/failed locator
→ validation result multiple/none/stale
→ no browser execution if ambiguous
→ recovery_needed or clarification_needed
→ user selects candidate/update_locator
→ backend validates updated locator
→ retry allowed only after accepted update
```

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | owns validation/recovery/update command acceptance |
| DEV-2 LLM/DOM | suggests candidates only |
| DEV-3 Frontend | renders candidate/recovery UI |
| DEV-4 E2E | uses weak/dynamic fixtures to prove no blind execution |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP007-E-001 | E2E | duplicate CTA | no execution; ambiguity shown |
| MVP007-E-002 | E2E | update locator accepted | retry allowed |
| MVP007-E-003 | E2E | update locator rejected | recovery remains |
| MVP007-E-004 | E2E | recovery open | no run_completed |

## Edge cases

- hidden candidate
- wrong page
- stale validation after navigation
- unsupported iframe/upload target

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

First Codex task for MVP-007 should be read-only:

```text
Read MVP-007, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for Locator ambiguity and recovery flow.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
