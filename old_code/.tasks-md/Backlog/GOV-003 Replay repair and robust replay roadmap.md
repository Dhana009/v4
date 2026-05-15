# GOV-003 Replay repair and robust replay roadmap

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** BE-012, REC-008, E2E-010, TRACE-007  
**Blocks:** future advanced capability work  
**Blocked By:** replay smoke not stable  
**Version:** Batch 11 v1  

---

## Product contribution

Scopes robust replay repair as a later roadmap item separate from P0 replay smoke.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-012 | replay smoke baseline only | robust repair is later | roadmap not implementation |
| REC-008 | archive baseline feeds replay | repair depends on stable recording/archive | dependency required |
| Handoff | do not add replay repair before recording stable | sequence after MVP | governance gate |
| TRACE-007 | replay failures traced | repair roadmap uses evidence | source gaps |

---

## Architecture boundary

Replay repair is P1/P2 until replay smoke, recording, archive, and trace evidence are stable.

---

## Contract / classification model

Roadmap phases:

| Phase | Scope |
|---|---|
| P0 | replay one/smoke with precondition failure |
| P1 | locator refresh/update during replay |
| P1 | wrong-page guided recovery |
| P2 | modal/dropdown state reconstruction |
| P2 | full replay-all session restore |
| Research | self-healing replay repair |

Implementation prerequisites:
stable recorded archive, replay events, trace evidence, fixtures, recovery UI.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| BE-012 | upstream | replay baseline |
| REC-008 | upstream | archive |
| TRACE-007 | upstream | replay failure evidence |
| E2E-010 | upstream | replay smoke tests |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | owns replay backend roadmap |
| DEV-2 | may propose repair suggestions, not truth |
| DEV-3 | owns replay recovery UI later |
| DEV-4 | owns replay repair fixtures |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV003-A-001 | Audit | replay repair requested before smoke | defer |
| GOV003-A-002 | Audit | replay failure trace | creates candidate roadmap item |
| GOV003-C-001 | Contract | repair lacks archive | blocked |

---

## Edge cases

- replay all flaky
- missing recorded child
- modal precondition
- same-page dynamic state

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

First Codex task for GOV-003 should be read-only:

```text
Read GOV-003, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
