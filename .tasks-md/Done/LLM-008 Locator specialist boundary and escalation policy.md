# LLM-008 Locator specialist boundary and escalation policy

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
**Dependencies:** LLM-001, LLM-003, LLM-004, BE-006  
**Blocks:** DOM/locator epic, execution validation  
**Version:** Batch 04 v1  

---

## Product contribution

This story defines when and how a locator specialist may help without owning locator truth.

## Architecture decision

Fixed:

- deterministic locator evidence first
- locator specialist suggests candidates/explanations only
- backend/browser validation decides final locator
- ambiguous locator asks user or routes recovery
- no action execution from locator specialist

## Locator specialist output schema

| Field | Required |
|---|---|
| target_summary | Yes |
| candidate_locators | Yes |
| recommended_candidate_id | Optional |
| ambiguity_reason | Optional |
| needs_user_selection | Yes |
| confidence | Yes |
| validation_requirements | Yes |

### Candidate locator

| Field | Required |
|---|---|
| candidate_id | Yes |
| strategy | role/label/text/testid/css/xpath/etc. |
| selector_or_locator | Yes |
| scope | Optional |
| rationale | Yes |
| risk | low/medium/high |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM008-C-001 | Contract | valid candidates | accepted |
| LLM008-C-002 | Contract | candidate executes action | rejected |
| LLM008-U-001 | Unit | deterministic evidence sufficient | no LLM needed |
| LLM008-U-002 | Unit | ambiguous candidates | needs_user_selection |
| LLM008-I-001 | Integration | candidate to backend validation | backend decides |

## Edge cases

- duplicate CTA text
- nested span target
- code block assertion
- hidden element candidate
- dynamic list/table row

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

First Codex task for LLM-008 should be read-only:

```text
Read LLM-008, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
