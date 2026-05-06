# GOV-008 Frontend UX polish and recovery actions roadmap

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** EPIC-005, FE-005, FE-008, TRACE-008  
**Blocks:** future advanced capability work  
**Blocked By:** MVP UI not stable  
**Version:** Batch 11 v1  

---

## Product contribution

Scopes frontend polish and richer recovery actions after Shadow DOM MVP functionality is stable.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-005 | Shadow DOM frontend is product target | polish after core typed UI | roadmap |
| FE-005 | clarification/recovery UI baseline | richer actions later | recovery roadmap |
| FE-008 | picker candidate UI baseline | UX improvements later | picker roadmap |
| Handoff | frontend recovery UX minimal | known future action area | classified roadmap |

---

## Architecture boundary

UX polish cannot create frontend-owned truth. All actions remain backend command envelopes.

---

## Contract / classification model

Roadmap actions:

| UX item | Priority |
|---|---|
| retry correction again | P1 |
| use original plan | P1 |
| edit pending step | P1 |
| cancel correction | P1 |
| richer recovery action cards | P1 |
| responsive layout polish | P2 |
| trace filtering/export polish | P2 |
| onboarding/help hints | P2 |

All actions must map to typed backend commands.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| FE-005 | upstream | recovery UI baseline |
| FE-008 | upstream | picker UI |
| TRACE-008 | upstream | diagnostic UI |
| EVENT-002 | upstream | command envelope |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | validates recovery commands |
| DEV-2 | may provide explanation text |
| DEV-3 | owns UX implementation |
| DEV-4 | tests UI actions and no local truth |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV008-A-001 | Audit | recovery action requested | map to command |
| GOV008-C-001 | Contract | UI action mutates state | rejected |
| GOV008-E-001 | E2E | retry correction command | backend validated |

---

## Edge cases

- duplicate action click
- stale recovery option
- optimistic UI success
- command rejected

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

First Codex task for GOV-008 should be read-only:

```text
Read GOV-008, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
