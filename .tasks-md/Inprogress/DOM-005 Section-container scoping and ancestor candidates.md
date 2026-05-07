# DOM-005 Section-container scoping and ancestor candidates

**Type:** Story  
**Status:** Inprogress  
**Priority:** P0  
**Epic:** EPIC-004 DOM and Locator Strategy  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** DOM-001, DOM-002, EPIC-004  
**Blocks:** DOM-003, picker UI, weak DOM flows  
**Version:** Batch 05 v1  

---

## Product contribution

This story fixes weak picker/locator behavior by exposing useful ancestor/container candidates instead of only the exact clicked node.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| Handoff | picker may capture nested spans/token text instead of useful ancestor container/code/pre/section/card/dialog/form/table row | include ancestor candidates |
| SOURCE-001 | scoped text and page/section context are deterministic evidence | use containers for locator scoping |

## Architecture decision

Fixed:

- selected element is not automatically final target
- ancestor candidates include interactive parent, row/card/form/dialog/section/code block where applicable
- user/frontend may choose target level, backend validates
- weak DOM gets explicit risk flags

## Ancestor candidate levels

| Level | Example |
|---|---|
| exact node | span/text/icon |
| interactive ancestor | button/link/input |
| component ancestor | card/list item/table row |
| form/dialog ancestor | form/modal |
| section ancestor | named page section |
| page landmark | nav/main/footer |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM005-U-001 | Unit | span inside button | button ancestor candidate |
| DOM005-U-002 | Unit | text in code block | code/pre ancestor |
| DOM005-U-003 | Unit | table row button | row ancestor |
| DOM005-U-004 | Unit | duplicate CTA cards | card/section scope |
| DOM005-I-001 | Integration | picker target levels | candidates returned |

## Edge cases

- deeply nested Elementor DOM
- SVG icon button
- table action button
- modal section
- repeated cards

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

First Codex task for DOM-005 should be read-only:

```text
Read DOM-005, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
