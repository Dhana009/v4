# PLAN-001 Delivery Control Model

**Type:** Planning Control  
**Status:** Planning  
**Priority:** P0  
**Owner:** Planning Brain  
**Applies To:** All workstreams  

---

## 1. Purpose

This document defines how work moves from source-grounded planning to implementation.

AutoWorkbench cannot be built through isolated tasks because the architecture is tightly connected:

```text
Backend truth
→ typed event contract
→ LLM runtime controller
→ Shadow DOM frontend
→ E2E harness
→ recording/codegen/replay
```

Delivery control protects the project from hidden drift.

---

## 2. Tasks.md board model

Tasks.md lanes:

```text
Planning
Backlog
Ready
In Progress
Review
Blocked
Done
```

Lane meaning:

| Lane | Meaning |
|---|---|
| Planning | Source packs, epics, process docs, architecture decisions |
| Backlog | Stories planned but not ready for implementation |
| Ready | Story has enough detail for repo inspection or implementation |
| In Progress | Codex/developer is actively working |
| Review | Work is done and evidence is awaiting validation |
| Blocked | Source/implementation/dependency gap exists |
| Done | Accepted with evidence |

---

## 3. Artifact types

| Prefix | Meaning | Lane default |
|---|---|---|
| SOURCE-* | Source pack / architecture memory | Planning |
| PLAN-* | Delivery control / template / governance | Planning |
| EPIC-* | Product capability group | Planning |
| BE-* | Backend story | Backlog |
| EVENT-* | Event/command contract story | Backlog |
| LLM-* | LLM runtime story | Backlog |
| DOM-* | DOM/locator story | Backlog |
| FE-* | Frontend story | Backlog |
| E2E-* | Harness/fixture story | Backlog |
| REC-* | Recording/codegen/replay story | Backlog |
| TRACE-* | Observability story | Backlog |
| CAP-* | Advanced capability story | Backlog |
| GAP-* | Gap/risk/decision item | Blocked or Planning |

---

## 4. Readiness levels

### Planning-ready

The story has enough planning information to review.

### Ready for repo inspection

The story tells Codex what to inspect, what to report, and what not to change.

### Ready for implementation

The repo-inspection result has confirmed:

- exact files/modules
- current behavior
- tests to add
- narrow change path
- no unresolved architecture conflict

### Ready for review

Implementation has produced evidence.

### Done

Acceptance criteria and validation evidence are accepted.

---

## 5. Four-developer delivery model

| Developer | Workstream | Primary branch |
|---|---|---|
| DEV-1 | Backend Runtime + Event Truth | `feature/backend-runtime-foundation` |
| DEV-2 | LLM Runtime Controller + DOM/Page Policy | `feature/llm-runtime-controller` |
| DEV-3 | Shadow DOM Frontend + Typed Rendering | `feature/shadow-dom-ui` |
| DEV-4 | E2E Harness + Fixtures + Evidence | `feature/e2e-fixtures-harness` |

Integration branch:

```text
integration/complete-llm-mode
```

Main branch receives only accepted work.

---

## 6. Coordination rule

Every story must name:

- primary owner
- affected workstreams
- upstream dependencies
- downstream dependents
- parallel work allowed
- conflict zones
- blocked work

No developer should need to guess whether their work is safe to start.

---

## 7. Codex role

Codex is implementation/repo-inspection worker.

Codex may:

- read approved planning files
- inspect repo
- write tests
- implement approved story
- report evidence

Codex must not:

- invent architecture
- override PRD/spec/handoff
- silently expand scope
- mutate planning quality gates
- continue through ambiguity

---

## 8. Batch strategy

Generate planning in small reviewed batches:

| Batch | Content |
|---|---|
| Batch 01 v2 | Planning foundation + EPIC-001 + BE-001 gold-standard |
| Batch 02 | BE-002 to BE-012 |
| Batch 03 | EPIC-002 + EVENT stories |
| Batch 04 | EPIC-003 + LLM stories |
| Batch 05 | EPIC-004 + DOM/locator stories |
| Batch 06 | EPIC-005 + FE stories |
| Batch 07 | EPIC-006 + E2E harness stories |

Do not generate broad backlog blindly. Validate one format first.
