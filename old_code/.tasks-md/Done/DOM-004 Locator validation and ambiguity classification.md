# DOM-004 Locator validation and ambiguity classification

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
**Dependencies:** DOM-002, DOM-003, BE-006, EVENT-005  
**Blocks:** execution contract, recovery, update_locator flow  
**Version:** Batch 05 v1  

---

## Product contribution

This story validates locator candidates in the browser and classifies ambiguity before execution.

## Architecture decision

Fixed:

- backend/browser validation is final locator truth
- validation returns unique/multiple/none/stale/hidden/disabled/wrong_page/unsupported
- LLM confidence does not replace validation
- ambiguity routes to user clarification or recovery

## Validation result schema

| Field | Required | Meaning |
|---|---|---|
| locator_ref | Yes | locator candidate reference |
| status | Yes | unique/multiple/none/stale/hidden/disabled/wrong_page/unsupported |
| match_count | Yes | number of matches |
| visible_count | Optional | visible matches |
| selected_element_ref | Conditional | unique valid match |
| ambiguity_candidates | Optional | when multiple |
| failure_reason | Optional | reason |
| evidence_ref | Optional | screenshot/trace/dom ref |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM004-U-001 | Unit | unique locator | status unique |
| DOM004-U-002 | Unit | multiple matches | status multiple |
| DOM004-U-003 | Unit | no match | status none |
| DOM004-U-004 | Unit | hidden match | status hidden |
| DOM004-U-005 | Unit | wrong page | status wrong_page |
| DOM004-I-001 | Integration | action before validation | blocked |

## Edge cases

- detached element after validation
- multiple visible exact matches
- locator unique but disabled
- validation across navigation
- iframe unsupported

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

First Codex task for DOM-004 should be read-only:

```text
Read DOM-004, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
