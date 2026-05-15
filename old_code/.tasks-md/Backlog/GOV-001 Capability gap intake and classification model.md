# GOV-001 Capability gap intake and classification model

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** EPIC-009, TRACE-007, TRACE-010, PLAN-003  
**Blocks:** future advanced capability work  
**Blocked By:** MVP gate evidence or trace export missing  
**Version:** Batch 11 v1  

---

## Product contribution

Defines how unsupported behavior becomes a classified backlog item instead of hidden failure or scope creep.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| PLAN-003 | capabilities are classified P0/P1/P2 | every gap must be classified | classification model |
| TRACE-007 | capability-gap trace evidence exists | intake consumes gap evidence | source reference required |
| TRACE-010 | redaction policy protects evidence | gap details must be safe | safe backlog entries |
| SOURCE-001 | capability gaps logged under active workspace when actionable | do not lose unsupported behavior | gap intake process |

---

## Architecture boundary

Gap intake is planning evidence only. It does not imply implementation approval.

---

## Contract / classification model

Classification fields:

| Field | Required |
|---|---|
| gap_id | Yes |
| source_trace_id/evidence_ref | Yes |
| capability_area | Yes |
| requested_behavior | Yes |
| current_support | unsupported/partial/supported |
| user_impact | Yes |
| priority_candidate | P0/P1/P2/not planned |
| recommendation | defer/implement/research/reject |
| owner_stream | DEV-1/DEV-2/DEV-3/DEV-4 |
| test_strategy | Yes |
| privacy_review_needed | Yes/No |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| TRACE-007 | upstream | gap evidence |
| PLAN-003 | upstream | priority classification |
| GOV-002 | downstream | browser capabilities |
| GOV-010 | downstream | sequencing |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | classifies backend/runtime impact |
| DEV-2 | classifies LLM/DOM impact |
| DEV-3 | classifies UX impact |
| DEV-4 | defines evidence/test need |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV001-C-001 | Contract | valid gap intake | classified |
| GOV001-C-002 | Contract | missing evidence_ref | rejected |
| GOV001-C-003 | Contract | P0 promotion without approval | rejected |
| GOV001-A-001 | Audit | gap list export | safe and redacted |

---

## Edge cases

- duplicate gaps
- low-impact unsupported behavior
- sensitive gap evidence
- gap discovered during MVP flow

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

First Codex task for GOV-001 should be read-only:

```text
Read GOV-001, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
