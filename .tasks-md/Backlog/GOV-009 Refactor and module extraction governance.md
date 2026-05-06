# GOV-009 Refactor and module extraction governance

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** EPIC-001, EPIC-006, MVP-010  
**Blocks:** future advanced capability work  
**Blocked By:** MVP evidence missing  
**Version:** Batch 11 v1  

---

## Product contribution

Defines when and how fragile large modules can be refactored without changing behavior.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| Handoff | agent.py too large; refactor after V1 regression/freeze | refactor must wait for tests | governance |
| PLAN-005 | tests first | refactor needs regression harness | acceptance |
| SOURCE-001 | backend truth boundaries non-negotiable | extraction cannot change ownership | guardrail |
| MVP-010 | release gate evidence | refactor after behavior proof | sequencing |

---

## Architecture boundary

Refactor is not feature work. It extracts modules with behavior-preserving tests.

---

## Contract / classification model

Refactor candidates:

| Module area | Target |
|---|---|
| plan correction | runtime/plan_correction.py |
| execution contract | runtime/execution_contract.py |
| recording | runtime/recording.py |
| outcomes | runtime/outcomes.py |
| replay | runtime/replay.py |
| picker contract | runtime/picker_contract.py |
| agent orchestrator | orchestration only |

Rules:
one subsystem at a time; tests before extraction; no behavior changes unless explicitly approved.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| MVP-010 | upstream | behavior gate |
| EPIC-006 | upstream | E2E safety |
| EPIC-001 | upstream | backend truth boundary |
| future implementation | downstream | maintainability |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | owns backend refactor boundaries |
| DEV-2 | updates LLM runtime modules only with tests |
| DEV-3 | frontend refactor only after hooks stable |
| DEV-4 | regression gate owner |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV009-A-001 | Audit | refactor before MVP gate | blocked |
| GOV009-C-001 | Contract | no behavior change | required |
| GOV009-E-001 | Regression | before/after tests | same behavior |

---

## Edge cases

- hidden behavior change
- broad mixed refactor
- test gaps
- circular imports

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

First Codex task for GOV-009 should be read-only:

```text
Read GOV-009, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
