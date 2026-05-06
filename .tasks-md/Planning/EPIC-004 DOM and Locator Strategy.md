# EPIC-004 DOM and Locator Strategy

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Primary Consumers:** DEV-1 Backend Runtime, DEV-3 Shadow DOM Frontend, DEV-4 E2E Harness  
**Capability:** Page understanding, target identity, locator ranking, validation, ambiguity handling  
**Readiness:** Planning-ready; stories require repo inspection before implementation  
**Depends On:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, EPIC-002, EPIC-003, BE-001, BE-006, EVENT-002, EVENT-005, LLM-008  
**Version:** Batch 05 v1  

---

## 1. Product contribution

This epic makes browser automation reliable by defining how AutoWorkbench understands the page, identifies the correct target, ranks locator candidates, validates them in the browser, and handles ambiguity.

Final user value:

```text
User describes an action/assertion in natural language
→ system extracts useful DOM/page evidence
→ deterministic locator strategy finds candidates first
→ LLM may suggest only when needed
→ backend/browser validates final locator truth
→ execution/recording/codegen use stable locators
```

Without EPIC-004:

- weak DOM pages can produce wrong targets
- nested span text can be selected instead of useful ancestor containers
- assertions can accidentally use expected_outcome as target/value
- LLM may hallucinate locators
- frontend/picker may provide misleading element context
- E2E tests will pass only on toy pages

---

## 2. Final product workflow supported

| Workflow stage | DOM/locator contribution |
|---|---|
| page analysis | extracts page, section, element, and accessibility evidence |
| plan generation | supplies target candidates and constraints |
| plan review | shows meaningful target descriptions if needed |
| execution | validates locator before browser action/assertion |
| recovery | classifies ambiguity/wrong-page/missing-target failures |
| recording/codegen | preserves validated locator and evidence |
| E2E regression | uses realistic fixtures for weak/semantic DOM behavior |

---

## 3. Source evidence table

| Source | Extracted rule | Planning interpretation | EPIC-004 impact |
|---|---|---|---|
| SOURCE-001 | Deterministic evidence first: role, label, placeholder, alt/title, data-testid, scoped text, stable id, scoped CSS, page/section context, live validation count. | Locator ranking must be deterministic before LLM escalation. | Build semantic ranking and validation stories. |
| EPIC-003 / LLM-008 | Locator specialist suggests candidates only; backend/browser validates. | LLM does not own final locator truth. | Define escalation boundary and candidate schema. |
| Handoff | Picker target quality is weak; current capture may select nested spans/token text instead of useful ancestor containers. | Need section/container/ancestor candidate model. | DOM-005 becomes P0. |
| Handoff | expected_outcome is parent metadata only, never assertion target/value. | Assertion target classification must be explicit. | DOM-006 becomes P0. |
| Test strategy | Fixtures must replicate real-world DOM, not only toy pages. | Need fixture requirements before implementation. | DOM-010 becomes P0. |

---

## 4. Architecture decision

Fixed decisions:

- deterministic locator candidates before LLM escalation
- browser/backend validation decides final locator truth
- LLM locator specialist produces candidates/rationale only
- element identity includes target, ancestors, section/container context, and accessibility evidence
- locator ambiguity is explicit and recoverable
- assertion target and assertion expected value are separate
- expected_outcome remains metadata only
- real-world DOM fixtures are required for validation

Flexible implementation choices:

- exact DOM extraction module names
- exact candidate scoring weights
- whether ranking is rule-table, score model, or hybrid
- exact fixture storage path after repo inspection

Forbidden interpretations:

- LLM-generated selector executes without validation
- picker selected node is automatically final target
- raw innerText-only matching is sufficient
- assertion target is inferred from expected_outcome text
- frontend decides locator truth
- broad replay/repair or advanced iframe/popup/file support under this epic unless explicitly scoped

---

## 5. Story map

| Story | Purpose | Direct consumers |
|---|---|---|
| DOM-001 | page snapshot and extraction contract | all locator work |
| DOM-002 | element identity/candidate model | ranking, picker, planner |
| DOM-003 | semantic ranking policy | locator_find |
| DOM-004 | live validation and ambiguity classification | execution/recovery |
| DOM-005 | section/container scoping and ancestors | picker, weak DOM |
| DOM-006 | assertion target classification | action_assert/codegen |
| DOM-007 | dynamic UI state baseline | modal/dropdown/recovery |
| DOM-008 | locator specialist escalation | LLM-008, DOM stories |
| DOM-009 | update_locator command flow | recovery/replay/fixes |
| DOM-010 | real-world DOM fixture requirements | DEV-4 E2E |

---

## 6. Direct vs indirect dependency note

Direct blockers:

```text
DOM-001
DOM-002
DOM-003
DOM-004
DOM-006
DOM-010
```

Indirect downstream consumers:

```text
LLM journey planner
confirmed execution contract
recording/codegen
Shadow DOM picker UI
E2E harness
future replay repair
advanced browser capabilities
```

Parallel safe work:

```text
DEV-1 can validate backend execution contract with mock locator refs.
DEV-3 can build picker UI shell using mock candidate payloads.
DEV-4 can build fixture server and fixture pages before final locator algorithms.
```

---

## 7. Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | Validates final locator before execution and stores execution evidence |
| DEV-2 LLM/DOM | Primary owner of DOM extraction/ranking/escalation policy |
| DEV-3 Frontend | Displays candidates/picker context but does not decide locator truth |
| DEV-4 E2E | Owns realistic DOM fixtures and locator regression scenarios |

---

## 8. Epic acceptance criteria

EPIC-004 is accepted when:

- page snapshot/extraction contract exists
- element candidate model includes semantic/accessibility/ancestor evidence
- deterministic ranking policy exists
- validation classifies unique/multiple/none/stale/hidden/wrong-page
- section/container scoping handles weak DOM better than raw nested text
- assertion target classification separates target/value/metadata
- dynamic UI baseline covers modal/dropdown/toast/page-change detection at minimum classification level
- locator specialist escalation is advisory-only
- update_locator command flow is typed and backend-validated
- realistic fixtures cover semantic and weak DOM cases
- tests prove LLM cannot own locator truth

---

## 9. Stop conditions

Stop if:

- current DOM extractor cannot expose enough evidence and migration path is unclear
- locator validation depends on frontend-only state
- expected_outcome leaks into assertion target/value
- real-world fixture coverage is missing
- weak DOM cases require broad frontend redesign before backend contract
- unsupported capabilities should be capability_gap instead of guessed locator logic
