# LLM-007 Plan correction diff output contract

Status: Done  
Sprint: Sprint 0  


**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-003 LLM Runtime Controller  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** LLM-001, LLM-004, BE-007, EVENT-004  
**Blocks:** safe correction flow  
**Version:** Batch 04 v1  

---

## Product contribution

This story defines the LLM output contract for plan corrections.

## Architecture decision

Fixed:

- LLM outputs structured diff, not full plan overwrite
- backend applies/rejects diff
- invalid schema retries once then fail closed
- removals/reorders require explicit reason

## Correction diff output schema

| Field | Required |
|---|---|
| correction_intent | Yes |
| target_plan_id/version | Yes |
| operations | Yes |
| reasoning_summary | Optional |
| ambiguity | Optional |
| requires_user_clarification | Yes |

### Diff operation

| Field | Required |
|---|---|
| action | add/update/remove/reorder |
| target_type | step/operation |
| target_id | Conditional |
| patch | Conditional |
| position | Conditional |
| reason | Yes |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM007-C-001 | Contract | valid update diff | accepted |
| LLM007-C-002 | Contract | full plan replacement | rejected |
| LLM007-C-003 | Contract | remove without reason | rejected |
| LLM007-C-004 | Contract | invalid twice | fail closed |
| LLM007-I-001 | Integration | correction diff to BE-007 | backend validates |

## Edge cases

- reorder with dependency conflict
- correction target missing
- LLM drops child silently
- user correction ambiguous

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

First Codex task for LLM-007 should be read-only:

```text
Read LLM-007, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
