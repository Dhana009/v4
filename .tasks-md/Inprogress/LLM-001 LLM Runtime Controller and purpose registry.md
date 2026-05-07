# LLM-001 LLM Runtime Controller and purpose registry

**Type:** Story  
**Status:** In Progress  
**Priority:** P0  
**Epic:** EPIC-003 LLM Runtime Controller  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-003, EPIC-001, EPIC-002  
**Blocks:** LLM-002 to LLM-010, all LLM-mediated flows  
**Version:** Batch 04 v1  

---

## Product contribution

This story creates the single control point for all LLM calls.

Without LLM-001, LLM calls can remain scattered across feature code, making it impossible to enforce purpose, schema, tool, skill, telemetry, and backend validation rules.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| LLM Runtime Policy Spec | every LLM call declares purpose/context/tools/model/schema/retry/validator | create Runtime Controller |
| SOURCE-001 | LLM proposes only | controller blocks truth ownership |
| EPIC-001 | backend validates runtime truth | controller routes output to validator |
| EPIC-002 | typed command/event boundaries | controller cannot emit runtime events directly |

## Architecture decision

Fixed:

- all LLM calls go through `LLMRuntimeController` or equivalent
- purpose registry is allowlisted
- direct ad hoc LLM calls are migration targets
- purpose handler returns structured proposal/output, not runtime mutation

## Purpose registry baseline

| Purpose | Role | Truth boundary |
|---|---|---|
| intent_classifier | classify user intent/missing info | no state mutation |
| clarification_generator | ask user questions | backend emits clarification |
| journey_planner | propose plan | backend stores active plan |
| step_plan_normalizer | normalize steps | backend validates |
| plan_diff_editor | propose correction diff | backend applies/rejects |
| locator_specialist | suggest locator candidates | backend validates locator |
| recovery_diagnoser | suggest recovery | backend owns recovery state |
| user_response_writer | explain result | no runtime mutation |
| trace_summarizer | summarize evidence | no mutation |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM001-U-001 | Unit | unknown purpose | rejected |
| LLM001-U-002 | Unit | registered purpose | policy loaded |
| LLM001-U-003 | Unit | direct mutation field in output | rejected by validator |
| LLM001-I-001 | Integration | journey_planner call | routed through controller |
| LLM001-A-001 | Audit | find direct LLM call sites | report migration list |

## Edge cases

- nested LLM call bypasses controller
- old model router directly called
- purpose missing schema
- purpose has no backend validator

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

First Codex task for LLM-001 should be read-only:

```text
Read LLM-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
