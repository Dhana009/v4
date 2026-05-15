# EPIC-006 E2E Harness and Real-world Fixtures

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Primary Consumers:** DEV-1 Backend Runtime, DEV-2 LLM/DOM, DEV-3 Shadow DOM Frontend  
**Capability:** Product-level regression harness, realistic fixtures, event/UI/artifact evidence  
**Readiness:** Planning-ready; stories require repo inspection before implementation  
**Depends On:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, EPIC-002, EPIC-003, EPIC-004, EPIC-005  
**Version:** Batch 07 v1  

---

## 1. Product contribution

This epic proves AutoWorkbench works as an integrated product.

Final user value:

```text
A developer can change backend, LLM, DOM, frontend, recording, or replay code
→ run product-level regression flows
→ see backend events, Shadow DOM UI state, browser evidence, screenshots, traces, and failures
→ identify regressions before merging.
```

Without EPIC-006:

- unit tests may pass while the real product flow breaks
- LLM Mode plan/confirm/execute/record can drift silently
- Shadow DOM UI may render wrong state
- locator logic may work only on toy DOM
- Codex can implement stories without objective evidence

---

## 2. Final product workflow supported

| Workflow stage | E2E harness contribution |
|---|---|
| product startup | launches backend/frontend/browser consistently |
| user intent | drives LLM Mode input through UI/API as scoped |
| event truth | captures backend event stream |
| UI truth | asserts Shadow DOM rendering through stable hooks |
| DOM/locator | runs realistic fixture pages |
| execution | verifies backend execution contract effects |
| recovery/correction | asserts negative and repair flows |
| recording/code | verifies recorded steps and code_update |
| replay smoke | validates backend-owned replay baseline |
| evidence | saves logs, events, screenshots, traces, artifacts |

---

## 3. Source evidence table

| Source | Extracted rule | Planning interpretation | EPIC-006 impact |
|---|---|---|---|
| PLAN-005 | Testing is part of each story, not later QA. | Harness must support story acceptance. | Build product-level regression harness. |
| PLAN-005 | Real-world fixtures required, not toy-only. | Fixtures must include semantic and weak DOM pages. | E2E-004 through E2E-007 are P0. |
| SOURCE-001 | Backend owns runtime truth; frontend renders typed events. | E2E must assert backend events and UI rendering. | Event capture + Shadow DOM assertions required. |
| EPIC-004 | DOM/locator strategy must be fixture-backed. | Locator behavior needs realistic fixture pages. | fixture registry is required. |
| EPIC-005 | Shadow DOM UI needs stable hooks/accessibility. | E2E tests should use stable hooks. | UI harness required. |
| Handoff | Tests alone were not enough; live flows exposed missing contracts. | Need integrated manual/e2e regression evidence. | Include happy/negative/recovery/recording/replay flows. |

---

## 4. Architecture decision

Fixed decisions:

- E2E harness tests real product surfaces, not isolated fake components only.
- Backend event stream is captured and asserted.
- Shadow DOM UI is asserted through stable hooks/accessibility.
- Realistic local fixtures are CI-stable; live external sites are optional.
- LLM calls may be mocked/recorded where needed to reduce flake/cost, but backend validation must still be tested.
- Every failed E2E flow must produce actionable artifacts.
- Fixture data must be sanitized and deterministic.

Forbidden interpretations:

- E2E depends on live Playwright.dev or staging sites as mandatory CI dependency.
- frontend UI-only success is accepted without backend event evidence.
- backend-only success is accepted without UI evidence for frontend stories.
- LLM randomness is allowed to make core regression flaky.
- toy pages are enough for locator validation.

---

## 5. Story map

| Story | Purpose | Direct consumers |
|---|---|---|
| E2E-001 | product startup and orchestration | all E2E flows |
| E2E-002 | backend event stream capture/assertions | backend/event/frontend tests |
| E2E-003 | Shadow DOM UI harness/hooks | frontend UI tests |
| E2E-004 | fixture server/registry | all fixture tests |
| E2E-005 | Playwright-docs-style fixture | docs/code/nav assertions |
| E2E-006 | weak WordPress/Elementor fixture | weak DOM/lead magnet cases |
| E2E-007 | modal/dropdown/toast dynamic fixture | dynamic UI/recovery |
| E2E-008 | LLM Mode happy path | MVP regression |
| E2E-009 | correction/clarification/recovery | negative-path regression |
| E2E-010 | recording/code_update/replay smoke | output/replay regression |

---

## 6. Direct vs indirect dependency note

Direct blockers:

```text
E2E-001 Product startup harness
E2E-002 Event capture/assertion utilities
E2E-003 Shadow DOM UI harness
E2E-004 Fixture server/registry
```

Indirect consumers:

```text
BE/EVENT/LLM/DOM/FE story acceptance
future MVP flows
CI pipeline
manual regression checklist
handoff validation
```

Parallel safe work:

```text
DEV-1 can expose event logs/mock events.
DEV-2 can provide mocked LLM outputs.
DEV-3 can provide stable hooks.
DEV-4 can build harness/fixtures using mocks while product contracts finalize.
```

---

## 7. Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | Provides event stream, backend startup, deterministic test hooks/logs |
| DEV-2 LLM/DOM | Provides mocked/recorded LLM outputs and DOM fixture expectations |
| DEV-3 Frontend | Provides Shadow DOM hooks and UI state rendering |
| DEV-4 E2E | Primary owner; builds harness, fixtures, assertions, artifacts |

---

## 8. Epic acceptance criteria

EPIC-006 is accepted when:

- product startup harness exists
- backend events can be captured and asserted
- Shadow DOM UI state can be asserted through stable hooks
- fixture server and registry exist
- realistic fixture classes cover semantic, weak DOM, dynamic UI, code block, forms, cards/tables, and capability gaps
- happy path LLM Mode regression exists
- correction/clarification/recovery regression exists
- recording/code_update/replay smoke regression exists
- failed runs produce logs/screenshots/traces/event artifacts
- tests can run locally without live external site dependency
- Codex/dev evidence proves repeatability

---

## 9. Stop conditions

Stop if:

- backend/frontend startup cannot be automated without broad product changes
- event stream cannot be captured
- Shadow DOM hooks are unavailable and frontend story has not added them
- realistic fixture strategy is missing
- LLM calls cannot be mocked/recorded safely
- test results are not reproducible
