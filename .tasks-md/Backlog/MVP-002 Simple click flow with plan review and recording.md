# MVP-002 Simple click flow with plan review and recording

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, MVP-001, BE-005, BE-006, BE-009, EVENT-004, EVENT-005, EVENT-006, DOM-003, DOM-004, FE-004, FE-006, E2E-008  
**Blocks:** basic action acceptance and code_update validation  
**Version:** Batch 08 v1  

---

## Product contribution

This story validates the simplest useful automation: user asks to click a target, reviews a plan, confirms it, backend executes, records it, and code_update appears.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-005 | execution cannot start before confirmation | click must wait for confirm | assert no pre-confirm execution |
| BE-006 | confirmed plan is execution contract | click must match confirmed operation | assert step/operation ids |
| DOM-004 | backend/browser validates locator | click locator must validate unique | assert validation evidence |
| BE-009 | backend records from execution evidence | step_recorded after actual click | assert recording payload |

## Required flow

```text
intent: click <target>
→ mocked journey plan with one click operation
→ plan_ready
→ user confirm
→ locator validation unique
→ step_executing click
→ step_recorded parent with click child
→ code_update contains click
→ run_completed
```

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | validates confirm/execution/recording |
| DEV-2 LLM/DOM | provides click plan and locator candidate |
| DEV-3 Frontend | renders plan and recorded/code panels |
| DEV-4 E2E | asserts backend event + UI + target page evidence |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP002-E-001 | E2E | simple click | click executes after confirm |
| MVP002-E-002 | E2E | no click before confirm | no step_executing |
| MVP002-E-003 | E2E | recording payload | parent/child click recorded |
| MVP002-E-004 | E2E | code_update | Playwright click line |

## Edge cases

- target duplicated
- click changes page state
- locator validates but target disabled
- code_update before recording

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

First Codex task for MVP-002 should be read-only:

```text
Read MVP-002, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for Simple click flow with plan review and recording.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
