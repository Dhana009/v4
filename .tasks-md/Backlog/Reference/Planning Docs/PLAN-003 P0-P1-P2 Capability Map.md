# PLAN-003 P0-P1-P2 Capability Map

**Type:** Planning Control  
**Status:** Planning  
**Priority:** P0  
**Owner:** Planning Brain  
**Applies To:** Product roadmap  

---

## 1. Purpose

This file defines what we are building and in what priority.

---

## 2. P0 capabilities

P0 means the product cannot be trusted without it.

| Capability | Epic | Why P0 |
|---|---|---|
| Backend Runtime Truth | EPIC-001 | Prevents LLM/frontend from owning runtime truth |
| Typed Event Contract | EPIC-002 | Enables backend/frontend/trace/E2E consistency |
| LLM Runtime Controller | EPIC-003 | Prevents uncontrolled LLM calls/tool exposure |
| DOM/Locator Strategy | EPIC-004 | Browser automation reliability depends on locators |
| Shadow DOM Frontend | EPIC-005 | New UI target; legacy overlay is transitional |
| E2E Harness + Fixtures | EPIC-006 | Proves product works in realistic browser flows |
| Complete LLM Mode MVP Flows | EPIC-007 | User-facing core loop |
| Recording/Codegen Basics | EPIC-008 | Converts execution into Playwright code |
| Trace/Observability Basics | EPIC-009 | Makes failures diagnosable |
| Delivery/Skills Governance | EPIC-011 | Prevents future architecture drift |

---

## 3. P1 capabilities

| Capability | Epic | Reason deferred |
|---|---|---|
| Robust replay repair/versioning | EPIC-008 later stories | Recording/codegen must stabilize first |
| Full Steps Mode editing | EPIC-007/FE | Needs backend plan/step contracts first |
| Advanced browser capabilities | EPIC-010 | Needs core runtime before expansion |
| Multi-model specialists | EPIC-003/004 | Optional until core LLM path stable |
| Polished Trace UX | EPIC-009 | Basic trace is enough for P0 |

---

## 4. P2/later

Do not distract P0 with:

- browser extension packaging
- visual testing layer
- advanced dashboards
- external integrations
- large CI matrix
- full page-map persistence
- import existing test suites

---

## 5. Replay boundary decision

```text
P0 = replay smoke + backend-owned replay contract
P1 = robust replay repair/versioning
```

Reason:

Replay cannot become reliable until recording/codegen evidence is stable. But P0 must still prove replay is backend-owned, not frontend simulation.

---

## 6. Capability dependency order

```text
Delivery/source planning
→ Backend runtime truth
→ Event/command contract
→ LLM runtime controller
→ DOM/locator strategy
→ Shadow DOM frontend
→ E2E harness
→ Complete LLM Mode MVP flows
→ Recording/codegen basics
→ Replay smoke
→ Advanced capabilities
```

Parallelism is allowed only if contracts are mocked or stable.
