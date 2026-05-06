# GOV-007 Multi-model orchestration stabilization roadmap

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** EPIC-003, LLM-008, TRACE-004  
**Blocks:** future advanced capability work  
**Blocked By:** single-controller baseline not stable  
**Version:** Batch 11 v1  

---

## Product contribution

Scopes optional multi-model/specialist orchestration after the Runtime Controller is stable.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-003 | multi-model orchestration optional/stabilized | not core truth | roadmap |
| LLM-008 | locator specialist advisory-only | specialist agents suggest only | boundary |
| TRACE-004 | LLM telemetry traces purpose/model | multi-model needs observability | evidence |
| SOURCE-001 | backend validates truth | no model owns state | architecture guard |

---

## Architecture boundary

Multi-model agents are advisory or proposal generators behind LLM Runtime Controller. They cannot mutate runtime truth.

---

## Contract / classification model

Candidate specialists:

| Specialist | Scope |
|---|---|
| Page Intelligence / Locator Agent | candidate suggestions |
| Debug Agent | failure diagnosis |
| Codegen Reviewer | diagnostics only |
| Judge/Risk Agent | risk/advisory verdict |
| Trace Summarizer | evidence summary |

Prerequisites:
purpose registry, schemas, telemetry, backend validators, fail-closed policy.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| EPIC-003 | upstream | controller/purpose registry |
| TRACE-004 | upstream | telemetry |
| LLM-008 | upstream | specialist boundary |
| GOV-010 | downstream | sequencing |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | enforces backend validators |
| DEV-2 | owns specialist policies |
| DEV-3 | displays advisory outputs only |
| DEV-4 | tests fail-closed/specialist trace |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV007-A-001 | Audit | specialist bypasses controller | reject |
| GOV007-C-001 | Contract | specialist mutates state | forbidden |
| GOV007-I-001 | Integration | specialist output invalid | fail closed |

---

## Edge cases

- model disagreement
- high token cost
- specialist stale context
- hallucinated locator/code

---

## Standard artifact/evidence expectation

| Artifact/evidence | Required | Notes |
|---|---|---|
| source gap reference | Yes | trace/capability/E2E evidence that justified the story |
| classification result | Yes | P0/P1/P2/not planned |
| dependency map | Yes | upstream source story/epic |
| acceptance criteria | Yes | what would make the capability complete |
| stop condition | Yes | when not to implement |
| test strategy | Yes | unit/integration/E2E/manual expectation |

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current support for this capability
- existing partial implementation or unsupported gap evidence
- related trace/capability gap records
- affected backend/event/LLM/DOM/frontend/E2E modules
- risks and scope boundaries
- whether this belongs in P0, P1, P2, or not planned
- proposed narrow implementation path only if accepted for implementation

No implementation until the classification and repo-inspection result are reviewed.

---

## Stop conditions

Stop if:

- capability is being added without source evidence or gap evidence
- it would break backend-owned truth
- it requires frontend/LLM-owned runtime truth
- it expands P0 MVP without explicit approval
- it cannot be tested with deterministic local evidence
- it requires broad rewrite before contract/tests
- privacy/security/redaction implications are unclear

---

## Codex execution summary

First Codex task for GOV-007 should be read-only:

```text
Read GOV-007, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
