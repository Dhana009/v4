# LLM-002 Skill loading policy and minimal context pack

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-003 LLM Runtime Controller  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; MR-3C finalized  
**Dependencies:** LLM-001, SOURCE-001, skills policy  
**Blocks:** LLM-005 to LLM-009, token/cost guard  
**Version:** Batch 04 v1  

---

## Product contribution

This story prevents context bloat and skill drift by loading only mandatory core skills plus task-specific skills.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| Skills hardening | mandatory core + task-specific only; do not load all blindly | implement skill selection policy |
| SOURCE-001 | PRD + Architecture Contract wins conflicts | core skills always loaded |
| LLM policy | token optimization must not reduce correctness | context filtering must preserve safety |

## Architecture decision

Fixed:

- skill loading header is required for every LLM task
- mandatory core skills always included
- task-specific skills selected by purpose
- if required evidence/skill missing, stop and report
- do not load all skills blindly

## Skill policy contract

| Category | Examples | Rule |
|---|---|---|
| mandatory core | skill_usage_policy, architecture_contract, prd_scope_validation | always |
| backend/runtime | backend_step_runner, typed_event_contract | backend purposes |
| locator/DOM | locator_strategy, frontend/shadow as relevant | locator/page purposes |
| TDD/refactor | tdd_harness, refactor_safety | implementation tasks |
| safety | permission_safety | risky tools/actions |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM002-U-001 | Unit | purpose journey_planner | core + planner skills |
| LLM002-U-002 | Unit | unknown task | core only or stop |
| LLM002-U-003 | Unit | all skills requested blindly | rejected |
| LLM002-U-004 | Unit | missing core skill | stop condition |
| LLM002-I-001 | Integration | controller call includes skill header | present |

## Edge cases

- conflicting skill guidance
- task requires skill not installed
- user asks speed over safety
- context budget exceeded

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current LLM call sites
- current model routing and context assembly
- current skill loading behavior
- current tool exposure / tool filtering logic
- current structured output schemas and retry/failure behavior
- current telemetry/token logging
- current backend validation boundaries
- existing tests covering this behavior
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- LLM call ownership is unclear
- current code conflicts with source and migration path is unclear
- implementation would let LLM own runtime truth
- backend validator boundary is unclear
- tool exposure by phase cannot be determined
- skill loading policy conflicts with repo-local skills
- schema validation cannot be tested first
- implementation requires broad backend/frontend rewrite
- token/cost reduction would reduce correctness

---

## Codex comprehension checklist

After reading this story, Codex should be able to explain:

- what final product capability this story contributes
- what upstream story/epic unlocks it
- what downstream stories depend on it
- which developer owns it
- what LLM is allowed to do
- what LLM is forbidden to do
- what backend must validate
- what tests must be written first
- what repo inspection must report
- when to stop

---

## Codex execution summary

First Codex task for LLM-002 should be read-only:

```text
Read LLM-002, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
