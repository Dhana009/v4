# LLM-004 Structured output schema validation and retry policy

**Type:** Story  
**Status:** In Progress  
**Priority:** P0  
**Epic:** EPIC-003 LLM Runtime Controller  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** LLM-001, EVENT-003, BE-003  
**Blocks:** LLM-005 to LLM-009 structured outputs  
**Version:** Batch 04 v1  

---

## Product contribution

This story ensures LLM outputs are machine-checkable and safe. Invalid output does not silently mutate runtime.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| SOURCE-001 | invalid schema retry once then fail closed | implement retry/fail policy |
| BE-003 | commands are validated | LLM outputs must validate before command/state |
| EVENT-003 | structured rejection payload | invalid outputs produce structured errors |

## Architecture decision

Fixed:

- every LLM purpose has schema
- output validation happens before backend mutation
- invalid schema retries once
- second failure fails closed or asks user
- no partial silent apply unless explicit story permits

## Schema validation contract

| Field | Required |
|---|---|
| purpose | Yes |
| schema_id/version | Yes |
| raw_output_ref | Optional |
| parsed_output | Yes if valid |
| validation_status | valid/invalid/retry_failed |
| errors | list |
| retry_count | integer |
| backend_validator | required for runtime-impacting purpose |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM004-U-001 | Unit | valid output | accepted |
| LLM004-U-002 | Unit | invalid once | retry |
| LLM004-U-003 | Unit | invalid twice | fail closed |
| LLM004-U-004 | Unit | extra mutation field | rejected |
| LLM004-I-001 | Integration | invalid plan diff | no plan mutation |

## Edge cases

- model returns prose around JSON
- schema version mismatch
- retry returns different intent
- partial valid/invalid diff

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

First Codex task for LLM-004 should be read-only:

```text
Read LLM-004, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```
