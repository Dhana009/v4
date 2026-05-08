# DOM-002 Element identity and candidate model

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
**Dependencies:** DOM-001, EPIC-004  
**Blocks:** DOM-003, DOM-004, DOM-005, DOM-006, DOM-008  
**Version:** Batch 05 v1  

---

## Product contribution

This story defines what an element candidate is. It prevents the system from treating a raw DOM node or selected span as the whole target.

## Architecture decision

Fixed:

- element candidate includes semantic identity, accessibility evidence, text, ancestry, section scope, and locator candidates
- candidate is not executable until validation
- parent/ancestor candidates are explicit

## Candidate schema

| Field | Required | Meaning |
|---|---|---|
| candidate_id | Yes | stable candidate id |
| element_ref | Yes | backend/browser reference |
| role | Optional | ARIA/native role |
| accessible_name | Optional | name |
| text | Optional | visible text |
| label/placeholder/alt/title | Optional | semantic evidence |
| data_testid | Optional | test id |
| tag | Yes | DOM tag |
| attributes_summary | Optional | useful attrs only |
| visibility/enabled | Optional | state |
| ancestor_chain | Yes | useful parent candidates |
| section_ref | Optional | section/container |
| candidate_type | Yes | action_target/assertion_target/container/text_block |
| risk_flags | Optional | duplicate/hidden/weak/text-only |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM002-U-001 | Unit | button with label | candidate has role/name |
| DOM002-U-002 | Unit | nested span in button | ancestor button candidate included |
| DOM002-U-003 | Unit | card CTA duplicate | section_ref included |
| DOM002-U-004 | Unit | code block text | text_block candidate |
| DOM002-U-005 | Unit | hidden candidate | risk flag |

## Edge cases

- non-interactive span clicked by picker
- icon-only button
- duplicate cards
- table row action
- label text separate from input

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

First Codex task for DOM-002 should be read-only:

```text
Read DOM-002, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
