# EPIC-010 Advanced Capabilities and Backlog Governance

**Type:** Epic  
**Status:** Planning  
**Priority:** P1/P2 Governance  
**Owner:** Planning Brain / Cross-workstream Governance  
**Primary Consumers:** DEV-1 Backend, DEV-2 LLM/DOM, DEV-3 Frontend, DEV-4 E2E, future planning agents  
**Capability:** Controlled advanced backlog intake, P1/P2 classification, implementation sequencing, and handoff governance  
**Readiness:** Planning-ready; not implementation-ready  
**Depends On:** SOURCE-001, PLAN-001, PLAN-002, PLAN-003, PLAN-005, EPIC-001 through EPIC-009  
**Version:** Batch 11 v1  

---

## Product contribution

This epic prevents advanced work from destabilizing the MVP.

It converts unsupported capabilities, future improvements, and refactor needs into a controlled backlog:

```text
trace/capability evidence
→ classify P0/P1/P2/not planned
→ define source-aligned scope
→ define dependencies/tests
→ sequence after MVP gates
→ prevent random advanced work from entering implementation
```

Without EPIC-010:

- replay repair, advanced observed outcomes, picker redesign, multi-model agents, and refactors can enter too early
- Codex may treat future ideas as current P0 requirements
- capability gaps may be lost or implemented without evidence
- implementation sequencing can drift away from backend-owned truth

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Epic impact |
|---|---|---|---|
| PLAN-003 | P0/P1/P2 capability map separates MVP from later work. | Advanced capabilities need classification. | GOV-001/GOV-002 define intake and classification. |
| SOURCE-001 | Capability gaps must be traceable and not guessed. | Unsupported behavior becomes gap evidence. | Governance consumes trace/capability records. |
| Handoff | Do not expand replay/advanced observed outcome/full UI redesign before stabilization. | Advanced work is sequenced after MVP. | Roadmap stories are P1/P2 by default. |
| EPIC-009 | Trace outputs are evidence, not runtime truth. | Trace supports backlog decisions. | GOV stories consume trace evidence safely. |
| PLAN-005 | No work done without tests/evidence. | Future capability stories require test strategy. | Governance requires acceptance/test plan. |
| Refactor guidance | Refactor only after V1/MVP behavior freeze and tests. | Module extraction needs gate and sequencing. | GOV-009 controls refactor. |

---

## Architecture decision

Fixed:

- Advanced capability work is not P0 unless explicitly approved.
- Every advanced story must cite source/gap evidence.
- Trace/capability gaps are evidence for backlog, not runtime truth.
- Implementation starts only after classification and repo inspection.
- Refactor starts only after MVP regression evidence exists.
- Multi-model orchestration remains optional/stabilized, not core runtime truth.
- Backend-owned truth remains non-negotiable across all future work.

Forbidden:

- silently promoting P1/P2 into P0
- implementing capability gaps without classification
- adding replay repair before replay smoke/recording stability
- adding advanced observed outcome logic before baseline evidence
- broad frontend redesign before Shadow DOM MVP
- module refactor without regression safety

---

## Story map

| Story | Purpose |
|---|---|
| GOV-001 | capability gap intake/classification |
| GOV-002 | advanced browser capability policy |
| GOV-003 | replay repair roadmap |
| GOV-004 | session persistence/restore roadmap |
| GOV-005 | advanced observed outcome detection |
| GOV-006 | picker ancestor-selection enhancement |
| GOV-007 | multi-model orchestration stabilization |
| GOV-008 | frontend UX polish/recovery actions |
| GOV-009 | refactor/module extraction governance |
| GOV-010 | final planning handoff and sequencing |

---

## Direct vs indirect dependency note

Direct blockers before implementation sequencing:

```text
MVP-010 acceptance gate
EPIC-006 E2E evidence
EPIC-009 trace/export/redaction evidence
```

Advanced stories are allowed into implementation only after:

```text
classification approved
repo inspection complete
test strategy defined
scope does not violate backend-owned truth
```

---

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | Classifies backend/runtime/replay/persistence/refactor implications |
| DEV-2 LLM/DOM | Classifies LLM/locator/specialist/multi-model implications |
| DEV-3 Frontend | Classifies UX/frontend/picker/recovery-action implications |
| DEV-4 E2E | Defines evidence, fixtures, artifacts, regression gates |

---

## Epic acceptance criteria

EPIC-010 is accepted when:

- capability gap intake model exists
- advanced browser capability policy exists
- replay repair roadmap is scoped as P1/P2
- session persistence/restore roadmap is scoped
- advanced observed outcome roadmap is scoped
- picker enhancement roadmap is scoped
- multi-model orchestration roadmap is scoped
- frontend UX polish/recovery roadmap is scoped
- refactor governance exists
- final planning handoff/sequencing document exists

---

## Stop conditions

Stop if a governance story tries to implement a feature directly, expands MVP scope without approval, or lacks trace/source evidence.
