# DOM-001 Page snapshot and DOM extraction contract

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-004 DOM and Locator Strategy  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** SOURCE-001, EPIC-004, LLM-008  
**Blocks:** DOM-002, DOM-003, DOM-004, LLM-006, DEV-4 fixture validation  
**Version:** Batch 05 v1  

---

## Product contribution

This story defines the page snapshot and DOM extraction contract that all locator, planning, assertion, and recovery work depends on.

Without DOM-001, the system cannot reason about targets reliably, and LLM/context decisions may depend on noisy full DOM dumps.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| SOURCE-001 | deterministic evidence first | snapshot must expose semantic/accessibility evidence |
| LLM Runtime Policy | reduce irrelevant context only | extraction must be compact but correct |
| Handoff | picker/element_info weak today | inspect and improve extraction contract |
| Test strategy | realistic fixtures required | snapshot must work on weak/semantic fixtures |

## Architecture decision

Fixed:

- snapshot must be structured, not raw unbounded DOM
- snapshot includes page URL/title, visible text summary, landmarks/sections, interactive elements, forms, tables, dialogs, code blocks where relevant
- snapshot distinguishes visible/hidden/disabled where possible
- extraction must avoid massive token dumps
- extraction output is evidence for candidates, not final locator truth

## Snapshot contract

| Field | Required | Meaning |
|---|---|---|
| url | Yes | current page URL |
| title | Yes | page title |
| viewport | Optional | viewport size/device |
| landmarks | Optional | header/nav/main/footer/dialog sections |
| sections | Yes where available | page/ancestor grouping |
| interactive_elements | Yes | buttons/links/inputs/selects/etc. |
| text_blocks | Optional | significant text/code/pre blocks |
| forms | Optional | label/input groups |
| tables/lists/cards | Optional | structured containers |
| dynamic_state | Optional | modal/dropdown/toast/loading hints |
| extraction_warnings | Optional | truncated/unsupported/iframe/shadow notes |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM001-U-001 | Unit | semantic button page | button has role/name |
| DOM001-U-002 | Unit | weak div button | extracted as candidate with warning |
| DOM001-U-003 | Unit | code block page | code/pre block identified |
| DOM001-U-004 | Unit | huge page | compact/truncated with warning |
| DOM001-I-001 | Integration | fixture snapshot | deterministic JSON shape |

## Edge cases

- hidden elements
- duplicate text
- nested spans
- virtualized list
- shadow roots
- iframe present but unsupported
- page loading state

---

## Required skills

Codex must load:

```text
.autoworkbench/skills/00_skill_usage_policy.md
.autoworkbench/skills/00_architecture_contract.md
.autoworkbench/skills/01_prd_scope_validation.md
.autoworkbench/skills/typed_event_contract.md
.autoworkbench/skills/02_tdd_regression_harness.md
.autoworkbench/skills/03_refactor_safety.md
```

Also load DOM/locator/frontend skill files if present after repo inspection. Do not load all skills blindly.

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current DOM extraction functions
- current element_info / locator_find / locator_validate behavior
- current picker/ancestor behavior
- current assertion target handling
- current locator ranking/fallbacks
- current dynamic UI/modal/dropdown detection
- current fixtures/tests related to locators
- current frontend/backend event/command boundary for locator updates
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- current DOM/locator ownership is unclear
- implementation would let LLM own final locator truth
- backend/browser validation boundary is unclear
- locator ambiguity cannot be represented
- tests/fixtures cannot be created first
- expected_outcome would become assertion target/value
- implementation requires broad rewrite
- page state or iframe/popup/file capability exceeds P0 scope

---

## Codex execution summary

First Codex task for DOM-001 should be read-only:

```text
Read DOM-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
