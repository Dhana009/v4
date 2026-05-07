# LLM-005 Intent classification and clarification routing

**Type:** Story  
**Status:** In Progress  
**Priority:** P0  
**Epic:** EPIC-003 LLM Runtime Controller  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** LLM-001, LLM-002, LLM-004, EVENT-007  
**Blocks:** LLM-006 journey planner, clarification UI  
**Version:** Batch 04 v1  

---

## Product contribution

This story decides whether user input is ready for planning or needs clarification.

## Architecture decision

Fixed:

- intent classifier does not create plan directly
- missing information routes to clarification
- backend emits clarification_needed; LLM only proposes question/options
- no guessing for ambiguous target/scope/data

## Intent output schema

| Field | Required | Meaning |
|---|---|---|
| intent_type | Yes | create_plan/correction/question/replay/unknown |
| confidence | Yes | high/medium/low |
| missing_info | Yes | list |
| clarification_question | Conditional | question text |
| suggested_options | Optional | choices |
| risk_flags | Optional | permission/destructive/ambiguous |
| planner_ready | Yes | boolean |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM005-U-001 | Unit | clear automation intent | planner_ready true |
| LLM005-U-002 | Unit | ambiguous target | clarification |
| LLM005-U-003 | Unit | missing test data | clarification |
| LLM005-U-004 | Unit | low confidence | clarification |
| LLM005-I-001 | Integration | classifier clarification | EVENT-007 shape compatible |

## Edge cases

- user says “do it”
- multiple possible targets
- destructive request
- correction disguised as new plan

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

First Codex task for LLM-005 should be read-only:

```text
Read LLM-005, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
