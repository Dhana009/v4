# EPIC-007 Complete LLM Mode MVP Flows

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** Planning Brain / Cross-workstream  
**Primary Consumers:** DEV-1 Backend, DEV-2 LLM/DOM, DEV-3 Frontend, DEV-4 E2E  
**Capability:** Product-level MVP flows that prove Complete LLM Mode works end to end  
**Readiness:** Planning-ready; stories require repo inspection before implementation  
**Depends On:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, EPIC-002, EPIC-003, EPIC-004, EPIC-005, EPIC-006  
**Version:** Batch 08 v1  

---

## 1. Product contribution

This epic defines the minimum Complete LLM Mode product flows that must work before V1/MVP can be considered stable.

It converts the architecture work into user-visible acceptance scenarios:

```text
User gives natural-language automation instruction
→ system plans safely
→ user reviews/corrects/confirms
→ backend validates and executes
→ frontend renders backend truth
→ recording/code_update reflect actual evidence
→ E2E proves the full flow with artifacts
```

Without EPIC-007:

- individual backend/frontend/LLM/DOM/E2E stories may pass in isolation
- there is no shared definition of “MVP works”
- release readiness remains subjective
- old regressions can reappear unnoticed

---

## 2. Source evidence table

| Source | Extracted rule | Planning interpretation | Epic impact |
|---|---|---|---|
| SOURCE-001 | Backend owns lifecycle, execution truth, recording, completion. | MVP flows must assert backend event truth. | Every MVP flow requires backend event evidence. |
| SOURCE-001 | LLM thinks/proposes only. | LLM outputs must be mocked/validated proposals. | MVP flows must prove no LLM-owned runtime truth. |
| Frontend/UI Spec | Shadow DOM is frontend target. | MVP UI assertions target Shadow DOM, not legacy overlay. | Every UI flow uses FE hooks. |
| EPIC-004 | DOM/locator validation is deterministic-first and backend/browser validated. | MVP flows must include locator validation evidence. | Click/assert flows include locator proof. |
| EPIC-006 | E2E proves full product behavior with artifacts. | MVP stories must include event/UI/browser evidence. | MVP acceptance gate depends on E2E outputs. |
| Handoff | Manual/live flows exposed gaps that tests missed. | MVP must include exact text, correction, multi-step isolation, recovery. | MVP stories map to known regression checklist. |

---

## 3. MVP flow map

| Story | Flow | Purpose |
|---|---|---|
| MVP-001 | end-to-end run lifecycle smoke | prove orchestration and core event sequence |
| MVP-002 | simple click | basic action planning/execution/recording |
| MVP-003 | visible assertion | basic assertion without click |
| MVP-004 | exact text/code assertion | assertion semantics and expected value |
| MVP-005 | correction before confirmation | plan correction safety |
| MVP-006 | clarification before planning | no guessing when ambiguous |
| MVP-007 | locator ambiguity/recovery | validation/recovery path |
| MVP-008 | multi-step strict cursor | cross-step isolation |
| MVP-009 | save/load minimal smoke | session state baseline |
| MVP-010 | acceptance gate | release checklist and evidence rules |

---

## 4. Architecture decision

Fixed decisions:

- MVP acceptance requires backend event evidence and Shadow DOM UI evidence.
- MVP flows use deterministic/mocked LLM outputs unless explicitly testing live model route.
- Frontend success alone is not sufficient.
- Backend success alone is not sufficient for UI stories.
- MVP flows must produce artifact bundles.
- Known V1 regression checklist items are represented as MVP stories.
- Stories are not implementation-ready until repo inspection confirms exact seams.

Forbidden interpretations:

- declaring MVP complete from unit tests only
- relying on legacy overlay as primary UI target
- letting LLM emit `step_recorded` or `run_completed`
- treating replay-all or robust repair as MVP blocker
- accepting ambiguous locator without validation/recovery evidence

---

## 5. Direct vs indirect dependency note

Direct blockers:

```text
MVP-001
MVP-002
MVP-003
MVP-004
MVP-005
MVP-008
MVP-010
```

Indirect/supporting flows:

```text
MVP-006 clarification
MVP-007 recovery
MVP-009 save/load smoke
```

Parallel safe work:

```text
DEV-1 can inspect backend event/lifecycle support.
DEV-2 can inspect and provide mocked LLM outputs.
DEV-3 can inspect Shadow DOM UI hooks.
DEV-4 can map E2E harness and artifacts.
```

---

## 6. Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | Owns lifecycle, command validation, execution, recording, completion truth |
| DEV-2 LLM/DOM | Provides schemas/mocked outputs/locator candidates; cannot own runtime truth |
| DEV-3 Frontend | Renders backend truth and sends commands through Shadow DOM UI |
| DEV-4 E2E | Proves each flow with backend events, UI hooks, target-page evidence, and artifacts |

---

## 7. MVP acceptance criteria

EPIC-007 is accepted when:

- MVP-001 through MVP-010 repo inspections are complete
- accepted implementation stories have tests first
- all required MVP flows pass locally
- backend event sequences are captured
- Shadow DOM UI states are asserted
- target page actions/assertions are verified
- recording/code_update outputs are validated
- artifact bundles exist for pass/fail evidence
- known V1 regression checklist is covered
- open non-MVP gaps are documented as P1/P2/capability gaps

---

## 8. Stop conditions

Stop if:

- MVP acceptance cannot be proven with E2E evidence
- any flow requires frontend/LLM-owned truth
- exact text assertion semantics are ambiguous
- multi-step strict cursor cannot be observed
- correction flow can still execute stale plan
- artifact/evidence model is missing
