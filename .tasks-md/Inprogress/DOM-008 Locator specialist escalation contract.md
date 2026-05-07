# DOM-008 Locator specialist escalation contract

**Type:** Story  
**Status:** Inprogress  
**Priority:** P0  
**Epic:** EPIC-004 DOM and Locator Strategy  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** LLM-008, DOM-001, DOM-003, DOM-004  
**Blocks:** LLM locator specialist, recovery, EPIC-004  
**Version:** Batch 05 v1  

---

## Product contribution

This story defines when the system escalates to the LLM locator specialist and what the specialist may return.

## Architecture decision

Fixed:

- deterministic locator path runs first
- escalate only when ambiguity/insufficient evidence remains
- locator specialist suggests candidates/rationale only
- backend/browser validation decides final locator
- low confidence cannot execute

## Escalation triggers

| Trigger | Required behavior |
|---|---|
| multiple candidates | ask specialist or user depending evidence |
| no deterministic candidate | specialist suggests candidates if context sufficient |
| weak DOM target | include ancestor/section evidence |
| low confidence | ask user/request more DOM |
| unsupported capability | capability gap, not locator guess |
| hidden/dynamic target | classify and recover |

## Specialist output contract

| Field | Required |
|---|---|
| target_summary | Yes |
| candidate_locators | Yes |
| recommended_candidate_id | Optional |
| confidence | Yes |
| ambiguity_reason | Optional |
| needs_user_selection | Yes |
| validation_requirements | Yes |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM008-U-001 | Unit | deterministic unique | no escalation |
| DOM008-U-002 | Unit | duplicate CTA | escalation/ambiguity |
| DOM008-U-003 | Unit | low confidence | no execution |
| DOM008-U-004 | Unit | unsupported file upload | capability gap |
| DOM008-I-001 | Integration | specialist candidate validated | backend decides |

## Edge cases

- hallucinated selector
- no DOM evidence
- multiple same text elements
- hidden candidate
- locator suggestion too broad

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

First Codex task for DOM-008 should be read-only:

```text
Read DOM-008, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
