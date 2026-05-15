# LLM-010 LLM telemetry, token budget, and cost guard

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
**Dependencies:** LLM-001, LLM-002, LLM-004  
**Blocks:** trace/observability, cost control, regression evidence  
**Version:** Batch 04 v1  

---

## Product contribution

This story makes LLM usage observable and controlled without reducing correctness.

## Architecture decision

Fixed:

- every LLM call logs purpose/model/schema/tokens/latency/status
- token optimization cannot remove safety-critical context
- telemetry supports debugging and cost review
- failures include validation/retry outcome

## Telemetry schema

| Field | Required |
|---|---|
| call_id | Yes |
| purpose | Yes |
| model | Yes |
| schema_id/version | Conditional |
| message_count | Yes |
| estimated_input_tokens | Yes |
| estimated_output_tokens | Optional |
| tools_exposed_count | Yes |
| skills_loaded | Yes |
| latency_ms | Yes |
| validation_status | Yes |
| retry_count | Yes |
| error_code | Optional |

## Budget policy

| Situation | Required behavior |
|---|---|
| context too large | trim irrelevant context only |
| required skill missing | stop |
| required source missing | stop |
| low-value trace context | summarize |
| safety-critical context | keep |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| LLM010-U-001 | Unit | call telemetry | required fields logged |
| LLM010-U-002 | Unit | invalid schema retry | retry_count logged |
| LLM010-U-003 | Unit | context budget exceeded | safe trim |
| LLM010-U-004 | Unit | required skill removed | rejected/stop |
| LLM010-I-001 | Integration | controller call emits telemetry | traceable output |

## Edge cases

- streaming response
- model route fallback
- local model vs API model
- token estimator mismatch
- telemetry logging failure

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

First Codex task for LLM-010 should be read-only:

```text
Read LLM-010, SOURCE-001, PLAN-002, PLAN-005, EPIC-003, and required skills.
Do not edit code.
Do not inspect unrelated product areas.
Inspect current LLM runtime ownership and report a narrow implementation path.
Do not implement until the repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
