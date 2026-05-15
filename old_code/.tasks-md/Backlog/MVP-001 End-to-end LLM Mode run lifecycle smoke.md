# MVP-001 End-to-end LLM Mode run lifecycle smoke

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, E2E-001, E2E-002, E2E-003, FE-001, BE-001, EVENT-001  
**Blocks:** all MVP flow stories, MVP acceptance gate  
**Version:** Batch 08 v1  

---

## Product contribution

This story proves the product can start a Complete LLM Mode run and move through the core lifecycle with backend events and Shadow DOM UI evidence.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-001 | backend owns lifecycle truth | smoke must assert backend lifecycle events | capture event sequence |
| EPIC-002 | typed events/commands | smoke uses canonical event/command envelopes | assert payload shape |
| EPIC-005 | Shadow DOM renders backend truth | UI must reflect event state | assert FE hooks |
| EPIC-006 | E2E proves product behavior | smoke produces artifact bundle | require screenshots/logs |

## Required event sequence

```text
run_started
plan_ready
confirmed command observed or accepted
step_validating / step_executing where applicable
step_recorded or explicit terminal result
code_update where recording applies
run_completed
```

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | exposes lifecycle events and rejects invalid transitions |
| DEV-2 LLM/DOM | provides deterministic mocked planner output |
| DEV-3 Frontend | renders run/plan/execution statuses |
| DEV-4 E2E | captures event/UI/artifact evidence |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP001-E-001 | E2E | lifecycle smoke | required events in order |
| MVP001-E-002 | E2E | UI mirrors lifecycle | Shadow DOM statuses update |
| MVP001-E-003 | E2E | no run_completed early | completion only after terminal work |
| MVP001-E-004 | E2E | artifacts exist | events/screenshots/logs saved |

## Artifact expectations

```text
events.ndjson
commands.json
shadow-ui-before.png
shadow-ui-after.png
target-page-after.png
trace-summary.txt
```

## Edge cases

- backend starts but frontend not mounted
- plan_ready missing plan_version
- duplicate run_completed
- command rejected

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

First Codex task for MVP-001 should be read-only:

```text
Read MVP-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for End-to-end LLM Mode run lifecycle smoke.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
