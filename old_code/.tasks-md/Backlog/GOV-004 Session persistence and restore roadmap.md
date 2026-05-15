# GOV-004 Session persistence and restore roadmap

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** BE-001, MVP-009, REC-008, TRACE-009  
**Blocks:** future advanced capability work  
**Blocked By:** session support unclear  
**Version:** Batch 11 v1  

---

## Product contribution

Scopes save/load/session restore beyond MVP conditional smoke.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| MVP-009 | save/load is conditional smoke or typed gap | do not hide scope expansion | roadmap |
| REC-008 | persistence may be in-memory or typed gap | define later persistence path | classify |
| SOURCE-001 | storage defaults active workspace, hidden metadata under workspace/.autoworkbench | storage path must be source-aligned | governance |
| TRACE-009 | artifacts/export evidence | persistence work needs artifact proof | testable path |

---

## Architecture boundary

Full session persistence/restore is not automatic P0. It requires repo-supported storage path and tests.

---

## Contract / classification model

Roadmap scope:

| Capability | Default priority |
|---|---|
| save current run snapshot | P1 if not P0 |
| load recorded steps/code lines | P1 |
| restore active plan after refresh | P1/P2 |
| restore browser/page state | P2 |
| restore modal/dropdown state | P2 |
| cross-workspace session portability | P2/research |

Storage rule:
default active workspace; internal metadata may use workspace/.autoworkbench.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| MVP-009 | upstream | conditional smoke |
| REC-008 | upstream | archive shape |
| TRACE-009 | upstream | export artifacts |
| GOV-010 | downstream | sequencing |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | owns storage/session backend |
| DEV-2 | no runtime truth role |
| DEV-3 | renders restored read-model |
| DEV-4 | tests save/load/refresh flows |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV004-A-001 | Audit | save unsupported | typed gap |
| GOV004-A-002 | Audit | hardcoded .hermes path | reject |
| GOV004-C-001 | Contract | restore active plan | backend-owned state only |

---

## Edge cases

- refresh loses in-memory state
- stale plan restored
- browser state not restorable
- workspace path missing

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

First Codex task for GOV-004 should be read-only:

```text
Read GOV-004, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
