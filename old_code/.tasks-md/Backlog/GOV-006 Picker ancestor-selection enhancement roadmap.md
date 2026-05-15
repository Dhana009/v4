# GOV-006 Picker ancestor-selection enhancement roadmap

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** DOM-005, FE-008, TRACE-005  
**Blocks:** future advanced capability work  
**Blocked By:** basic picker candidate UI not complete  
**Version:** Batch 11 v1  

---

## Product contribution

Scopes richer picker ancestor selection after the baseline candidate model and UI are stable.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| DOM-005 | ancestor candidates needed for weak DOM | baseline exists first | enhancement roadmap |
| FE-008 | UI displays candidate levels | richer UX later | frontend roadmap |
| Handoff | picker target quality weak | known improvement area | roadmap evidence |
| TRACE-005 | ambiguity trace identifies picker problems | evidence-based prioritization | source gap |

---

## Architecture boundary

Picker enhancements help users choose targets but do not validate final locator truth.

---

## Contract / classification model

Enhancement candidates:

| Capability | Priority |
|---|---|
| show exact/ancestor levels | P0 baseline |
| visual hover highlight | P1 |
| compare candidate scopes | P1 |
| choose code/pre/card/row/dialog target | P1 |
| candidate confidence badges | P1 |
| inline locator preview | P2 |
| user-trained locator preference | P2/research |

Backend/browser validation remains final.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| DOM-005 | upstream | ancestor model |
| FE-008 | upstream | candidate UI |
| TRACE-005 | upstream | picker failure evidence |
| E2E-006 | downstream | weak DOM tests |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | validates selected candidate |
| DEV-2 | improves candidate/ranking model |
| DEV-3 | owns picker UX |
| DEV-4 | tests weak DOM/picker flows |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV006-A-001 | Audit | nested span issues | enhancement candidate |
| GOV006-C-001 | Contract | UI-selected target as final truth | rejected |
| GOV006-E-001 | E2E | ancestor level shown | candidate only |

---

## Edge cases

- long ancestor list
- duplicate candidate names
- visual highlight mismatch
- stale candidate

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

First Codex task for GOV-006 should be read-only:

```text
Read GOV-006, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
