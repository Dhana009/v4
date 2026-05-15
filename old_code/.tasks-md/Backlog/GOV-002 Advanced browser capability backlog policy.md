# GOV-002 Advanced browser capability backlog policy

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** EPIC-004, TRACE-007, GOV-001  
**Blocks:** future advanced capability work  
**Blocked By:** capability evidence missing  
**Version:** Batch 11 v1  

---

## Product contribution

Defines governance for advanced browser capabilities such as iframe, popup, file upload/download, browser permission prompts, and multi-tab behavior.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-004 | unsupported iframe/popup/upload routes capability_gap | do not guess advanced capabilities | classify backlog |
| TRACE-007 | replay/gap evidence captures unsupported capability | use evidence | source-based backlog |
| Handoff | do not add advanced capabilities before MVP stabilization | defer by default | P1/P2 policy |

---

## Architecture boundary

Advanced browser capabilities are P1/P2 unless MVP gate explicitly identifies a P0 blocker.

---

## Contract / classification model

Capability classes:

| Capability | Default priority |
|---|---|
| iframe handling | P1/P2 |
| popup/new tab | P1 |
| file upload/download | P1/P2 |
| browser permissions | P1 |
| downloads | P2 |
| drag/drop | P2 |
| canvas/non-DOM interactions | P2/research |
| cross-origin flows | P2/research |

Required before implementation:
source evidence, test fixture, backend ownership, event contract, recovery behavior.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| GOV-001 | upstream | classification model |
| DOM-007 | upstream | unsupported/dynamic evidence |
| TRACE-007 | upstream | gap trace |
| E2E fixtures | downstream | capability-specific tests |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | defines backend execution/recovery impact |
| DEV-2 | defines DOM/locator capability limits |
| DEV-3 | defines UI prompts/recovery choices |
| DEV-4 | defines capability fixtures/tests |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV002-A-001 | Audit | unsupported iframe gap | classified P1/P2 |
| GOV002-A-002 | Audit | upload requested in MVP | gap unless approved |
| GOV002-C-001 | Contract | capability lacks fixture | not implementation-ready |

---

## Edge cases

- capability required by customer flow
- unsupported but low impact
- security/privacy permission prompts
- cross-origin restrictions

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

First Codex task for GOV-002 should be read-only:

```text
Read GOV-002, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
