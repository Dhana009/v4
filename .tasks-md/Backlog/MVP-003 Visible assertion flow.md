# MVP-003 Visible assertion flow

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, MVP-001, BE-006, BE-009, DOM-006, EVENT-005, EVENT-006, FE-006, E2E-008  
**Blocks:** assertion-only acceptance  
**Version:** Batch 08 v1  

---

## Product contribution

This story validates assertion-only automation: user asks to assert something is visible and the system records an assertion without performing a click.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| DOM-006 | visible assertions are target-only | no expected text needed | assert target/value separation |
| BE-006 | operation must match confirmed plan | assertion operation validated | assert operation identity |
| BE-009 | recording must use backend evidence | assertion recorded after actual check | assert recorded child |
| Handoff | visible assertion should not become click | protect action/assertion distinction | no click event |

## Required flow

```text
intent: verify/assert <target> is visible
→ plan_ready with assertion operation
→ confirm
→ locator validation
→ action_assert visible
→ step_recorded with assertion child
→ code_update with expect(locator).toBeVisible()
→ run_completed
```

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | validates assertion operation and records evidence |
| DEV-2 LLM/DOM | outputs assertion plan only |
| DEV-3 Frontend | renders assertion recorded/code output |
| DEV-4 E2E | asserts no click and correct code_update |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP003-E-001 | E2E | visible assertion | assertion passes |
| MVP003-E-002 | E2E | no click emitted | no click operation |
| MVP003-E-003 | E2E | code_update | toBeVisible generated |
| MVP003-E-004 | E2E | expected_outcome metadata | not target/value |

## Edge cases

- hidden target
- duplicate visible text
- assertion target in section
- LLM outputs click instead of assert

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

First Codex task for MVP-003 should be read-only:

```text
Read MVP-003, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for Visible assertion flow.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
