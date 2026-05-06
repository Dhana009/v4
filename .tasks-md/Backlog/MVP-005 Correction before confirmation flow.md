# MVP-005 Correction before confirmation flow

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, MVP-001, BE-004, BE-005, BE-007, LLM-007, EVENT-004, FE-004, E2E-009  
**Blocks:** plan correction safety acceptance  
**Version:** Batch 08 v1  

---

## Product contribution

This story proves users can correct a proposed plan before execution and stale/old plans cannot execute.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-007 | correction uses structured diff, backend applies/rejects | correction must not silently overwrite | validate diff flow |
| BE-004 | active plan is versioned | revised plan gets new version | assert version changes |
| BE-005 | only current confirmed plan executes | stale plan blocked | assert old plan rejection |
| EPIC-005 | frontend renders revised plan only after backend event | UI cannot mutate locally | assert UI behavior |

## Required flow

```text
initial plan_ready
→ user correction: "assert first, then click"
→ LLM emits correction diff
→ backend validates/applies new plan version
→ revised plan_ready shown
→ confirm revised plan
→ only revised children execute in order
```

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | owns active plan versioning and diff application |
| DEV-2 LLM | outputs structured diff only |
| DEV-3 Frontend | sends correction and renders revised plan from backend |
| DEV-4 E2E | proves old plan cannot execute |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP005-E-001 | E2E | correction before confirm | revised plan_ready |
| MVP005-E-002 | E2E | old plan confirm | runtime_rejected |
| MVP005-E-003 | E2E | revised execution order | assert then click |
| MVP005-E-004 | E2E | invalid diff twice | fail closed |

## Edge cases

- correction during execution
- full plan overwrite
- child drop without reason
- duplicate correction

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

First Codex task for MVP-005 should be read-only:

```text
Read MVP-005, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for Correction before confirmation flow.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
