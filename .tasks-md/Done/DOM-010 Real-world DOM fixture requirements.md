# DOM-010 Real-world DOM fixture requirements

Status: Done  
Sprint: Sprint 0  


**Type:** Story  
**Status:** Done
**Priority:** P0  
**Epic:** EPIC-004 DOM and Locator Strategy  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** PLAN-005, EPIC-004  
**Blocks:** DEV-4 E2E harness, all DOM stories  
**Version:** Batch 05 v1  

---

## Product contribution

This story ensures DOM/locator work is tested against realistic pages, not only perfect fixtures.

## Architecture decision

Fixed:

- DOM/locator stories require realistic fixtures
- fixtures cover semantic and weak DOM behavior
- live external sites are optional, not hard CI dependency
- fixture content should be sanitized/captured where needed

## Fixture classes

| Fixture | Required scenarios |
|---|---|
| Playwright docs-style | sections, code blocks, nav, exact text |
| weak WordPress/Elementor-style | div/span CTAs, nested nodes, duplicate sections |
| lead-magnet form | labels, placeholders, validation, upload gap |
| modal/dropdown page | dialog/listbox/toast dynamic state |
| table/card dashboard | repeated rows/cards, scoped actions |
| accessibility semantic page | role/name/label/testid cases |

## Fixture acceptance

Each fixture should include:

- stable URL/path
- expected DOM features
- expected locator candidates
- expected ambiguity cases
- expected assertions
- negative cases
- fixture-specific test IDs where appropriate

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM010-F-001 | Fixture | docs code block | exact text target possible |
| DOM010-F-002 | Fixture | weak CTA nested span | ancestor candidate found |
| DOM010-F-003 | Fixture | duplicate cards | section scoping needed |
| DOM010-F-004 | Fixture | modal/dropdown | dynamic state detected |
| DOM010-F-005 | Fixture | table row action | row scope candidate |
| DOM010-I-001 | Integration | all fixtures load | deterministic paths |

## Edge cases

- fixture drift
- overly toy fixture
- live site unavailable
- huge DOM
- sensitive data in captured fixture

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

First Codex task for DOM-010 should be read-only:

```text
Read DOM-010, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
