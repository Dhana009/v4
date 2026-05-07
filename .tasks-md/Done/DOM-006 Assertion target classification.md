# DOM-006 Assertion target classification

**Type:** Story  
**Status:** Done
**Priority:** P0  
**Epic:** EPIC-004 DOM and Locator Strategy  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** DOM-001, DOM-002, DOM-004, BE-006  
**Blocks:** assertion execution, recording/codegen  
**Version:** Batch 05 v1  

---

## Product contribution

This story prevents assertion bugs by separating assertion target, assertion type, expected value, and expected_outcome metadata.

## Architecture decision

Fixed:

- expected_outcome is parent metadata only
- assertion target must come from DOM/locator evidence
- assertion expected value must come from user intent or validated plan child
- visible/present assertions cannot silently become text assertions
- text assertions require explicit expected text/value

## Assertion classification contract

| Field | Required | Meaning |
|---|---|---|
| assertion_type | Yes | visible/hidden/enabled/disabled/has_text/exact_text/has_value/checked/etc. |
| target_candidate_id | Yes | DOM target |
| expected_value | Conditional | text/value where needed |
| source_of_expected_value | Conditional | user intent/plan child |
| expected_outcome_metadata_ref | Optional | parent metadata only |
| compatibility_flags | Optional | e.g., visible+has_text invalid |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM006-U-001 | Unit | visible assertion | no expected text needed |
| DOM006-U-002 | Unit | has_text assertion | expected value required |
| DOM006-U-003 | Unit | expected_outcome text | not used as target/value |
| DOM006-U-004 | Unit | exact code block text | text_block target |
| DOM006-U-005 | Unit | visible + has_text conflict | rejected/normalized |
| DOM006-I-001 | Integration | assertion plan child | valid action_assert payload |

## Edge cases

- code command exact text
- section contains text
- duplicate target text
- dynamic generated analysis text
- whitespace-sensitive text

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

First Codex task for DOM-006 should be read-only:

```text
Read DOM-006, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
