# LLM-009 Recovery diagnoser output contract

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-003 LLM Runtime Controller  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** LLM-001, LLM-004, BE-008, EVENT-007  
**Blocks:** recovery UI and backend recovery decisions  
**Version:** Batch 04 v1  

---

## Product contribution

This story defines how LLM helps diagnose failure without resolving recovery truth.

## Architecture decision

Fixed:

- recovery diagnoser suggests cause/options
- backend owns recovery state
- LLM cannot mark resolved/skipped/completed
- unsupported capability becomes gap

## Recovery diagnosis schema

| Field | Required |
|---|---|
| failure_summary | Yes |
| likely_cause | Yes |
| suggested_options | Yes |
| recommended_option | Optional |
| needs_user_input | Yes |
| unsupported_capability | Optional |
| confidence | Yes |

### Suggested option

| Field | Required |
|---|---|
| option_id | Yes |
| option_type | retry/update_locator/skip/stop/clarify/gap |
| label | Yes |
| risk | low/medium/high |
| backend_validation_needed | Yes |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM009-C-001 | Contract | valid diagnosis | accepted |
| LLM009-C-002 | Contract | output says resolved | rejected |
| LLM009-C-003 | Contract | skip without backend validation | rejected |
| LLM009-I-001 | Integration | diagnosis to BE-008 | recovery options only |

## Edge cases

- stale page after failure
- locator changed
- permission issue
- unsupported capability
- repeated same failure

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

First Codex task for LLM-009 should be read-only:

```text
Read LLM-009, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
