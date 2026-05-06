# LLM-003 Tool exposure policy by runtime phase

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-003 LLM Runtime Controller  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** LLM-001, LLM-002, BE-001, BE-003, EVENT-002  
**Blocks:** safe LLM tool use, execution contract  
**Version:** Batch 04 v1  

---

## Product contribution

This story ensures LLM sees only tools that are safe for its purpose and current runtime phase.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| SOURCE-001 | backend validates/controls runtime truth | LLM tool access cannot bypass backend |
| Handoff | tool filtering alone is not enough; backend validation must enforce phases | define exposure policy plus backend validation |
| EVENT-002 | commands are typed requests | tool-like outputs must route through command/validator |

## Architecture decision

Fixed:

- planning phase tools differ from execution/recovery tools
- LLM cannot call browser-changing tools before confirmation
- tool exposure is deny-by-default
- backend validates every tool/command regardless of exposure filter

## Phase/tool policy baseline

| Phase | Allowed LLM capabilities | Forbidden |
|---|---|---|
| planning | analyze intent/context, propose plan | browser-changing actions |
| clarification | ask/interpret user answer | execution |
| plan_review | propose correction diff/explain | execution before confirm |
| executing | propose next expected operation only if backend asks | arbitrary action |
| recovery | diagnose/suggest recovery | mark resolved/completed |
| completed | summarize | mutate state |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM003-U-001 | Unit | planning phase browser action | not exposed/blocked |
| LLM003-U-002 | Unit | recovery phase completion tool | forbidden |
| LLM003-U-003 | Unit | unknown phase | deny by default |
| LLM003-I-001 | Integration | LLM emits action before confirm | backend blocks |
| LLM003-I-002 | Integration | allowed locator suggestion | backend validates later |

## Edge cases

- phase changes during LLM call
- correction while execution active
- tool exposed by legacy router
- LLM calls tool not in declared purpose

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

First Codex task for LLM-003 should be read-only:

```text
Read LLM-003, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
