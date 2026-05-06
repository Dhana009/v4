# GOV-005 Advanced observed outcome detection roadmap

**Type:** Story  
**Status:** Backlog  
**Priority:** P1/P2 Governance  
**Epic:** EPIC-010 Advanced Capabilities and Backlog Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection or backlog classification; not ready for implementation  
**Dependencies:** REC-007, TRACE-002, TRACE-005  
**Blocks:** future advanced capability work  
**Blocked By:** baseline observed outcome missing  
**Version:** Batch 11 v1  

---

## Product contribution

Scopes advanced observed outcome detection beyond the P0 basic before/after URL/title and simple matched_expected summary.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| REC-007 | observed_outcome is evidence/summary, not assertion source | advanced detection remains evidence | scope guard |
| Handoff | modal/dropdown/toast/download/content-change detection future work | defer advanced detection | roadmap |
| TRACE-005 | DOM/dynamic evidence exists | use trace evidence safely | future inputs |
| SOURCE-001 | token optimization must not reduce correctness | advanced detection cannot guess success | validation required |

---

## Architecture boundary

Observed outcome detection remains diagnostic evidence. It cannot become completion truth or assertion value by itself.

---

## Contract / classification model

Roadmap classes:

| Detection | Priority |
|---|---|
| URL/title before-after | P0 baseline |
| visible content change | P1 |
| modal/dialog appeared | P1 |
| dropdown/listbox opened | P1 |
| toast/alert appeared | P1 |
| download started/completed | P2 |
| file picker opened | P2 |
| network/API side effect | P2/research |
| semantic generated text validation | P2/research |

Required rule:
completion still comes from backend run completion guard, not observed_outcome alone.

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-007 | upstream | outcome metadata |
| DOM-007 | upstream | dynamic state baseline |
| TRACE-005 | upstream | DOM evidence |
| E2E fixtures | downstream | observed-outcome tests |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | owns outcome persistence/guardrails |
| DEV-2 | may classify semantic outcomes advisory-only |
| DEV-3 | displays observed outcome evidence |
| DEV-4 | creates dynamic outcome fixtures |

---

## Test / evidence strategy

| Test/Evidence ID | Layer | Scenario | Expected |
|---|---|---|---|
| GOV005-A-001 | Audit | modal observed outcome request | classify P1 |
| GOV005-C-001 | Contract | observed_outcome marks completion | rejected |
| GOV005-E-001 | E2E | toast fixture | outcome evidence only |

---

## Edge cases

- transient toast
- no visible change
- generated text
- false positive content change

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

First Codex task for GOV-005 should be read-only:

```text
Read GOV-005, SOURCE-001, PLAN-002, PLAN-003, PLAN-005, EPIC-010, and relevant upstream epics.
Do not edit code.
Do not implement.
Classify current capability support and report whether this is P1/P2/not planned.
Only propose implementation after classification is reviewed.
```
