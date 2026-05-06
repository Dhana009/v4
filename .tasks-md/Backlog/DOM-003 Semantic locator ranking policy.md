# DOM-003 Semantic locator ranking policy

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-004 DOM and Locator Strategy  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** DOM-001, DOM-002, EPIC-004  
**Blocks:** DOM-004, DOM-008, BE-006 execution validation  
**Version:** Batch 05 v1  

---

## Product contribution

This story defines deterministic ranking of locator candidates before LLM escalation.

## Architecture decision

Fixed ranking preference:

```text
data-testid where approved/stable
role + accessible name
label / placeholder
alt/title
scoped exact text
section/container scoped locator
stable id
scoped CSS fallback
XPath only as last resort/diagnostic
```

LLM can suggest candidate ranking only when deterministic evidence is insufficient.

## Ranking contract

| Signal | Preferred use | Risk |
|---|---|---|
| data-testid | stable automation target | bad if generated/dynamic |
| role/name | primary Playwright style | duplicate names |
| label | form controls | label association missing |
| placeholder | fallback for inputs | placeholder changes |
| scoped text | assertions/links/buttons | duplicate text |
| stable id | fallback | dynamic ids |
| CSS | scoped fallback | brittle |
| XPath | last resort | brittle |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM003-U-001 | Unit | role/name exists | ranked first |
| DOM003-U-002 | Unit | duplicate text in sections | scoped candidate preferred |
| DOM003-U-003 | Unit | data-testid available | high rank |
| DOM003-U-004 | Unit | dynamic class only | risk high |
| DOM003-U-005 | Unit | XPath candidate | last resort |

## Edge cases

- same accessible name multiple times
- generated IDs
- empty accessible name
- icon-only button
- multilingual text

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

First Codex task for DOM-003 should be read-only:

```text
Read DOM-003, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
