# LLM-006 Journey planner output contract

**Type:** Story  
**Status:** Testing  
**Priority:** P0  
**Epic:** EPIC-003 LLM Runtime Controller  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** LLM-001, LLM-004, LLM-005, BE-004, EVENT-004  
**Blocks:** active plan store, plan_ready UI, execution contract  
**Version:** Batch 04 v1  

---

## Product contribution

This story defines what the journey planner may output as a plan proposal.

## Architecture decision

Fixed:

- journey planner proposes plan only
- backend validates/stores active plan
- plan includes ordered steps and child operations
- expected_outcome is metadata only
- no execution permission from planner output

## Journey plan schema

| Field | Required | Meaning |
|---|---|---|
| plan_intent | Yes | user-level goal |
| steps | Yes | ordered planned steps |
| assumptions | Optional | explicit assumptions |
| clarifications_needed | Optional | missing info |
| risks | Optional | permission/ambiguity |
| confidence | Yes | high/medium/low |

### Planned step

| Field | Required |
|---|---|
| proposed_step_id | Optional/backend may assign |
| intent | Yes |
| expected_outcome_metadata | Optional |
| children | Yes |
| precondition/postcondition | Optional |

### Planned operation

| Field | Required |
|---|---|
| type/subtype | Yes |
| target_semantic_name | Conditional |
| locator_candidate_ref | Optional |
| assertion_type/value | Conditional |
| order_index | Yes |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM006-C-001 | Contract | valid plan | accepted by schema |
| LLM006-C-002 | Contract | plan has execution_result | rejected |
| LLM006-C-003 | Contract | expected_outcome as assertion target | rejected |
| LLM006-I-001 | Integration | valid plan to BE-004 | active plan candidate |

## Edge cases

- plan with no children
- duplicate operation order
- assertion without expected value
- high confidence but missing target

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

First Codex task for LLM-006 should be read-only:

```text
Read LLM-006, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
