# DOM-007 Dynamic UI state detection baseline

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-004 DOM and Locator Strategy  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** DOM-001, DOM-004, EVENT-007  
**Blocks:** recovery, observed outcome, modal/dropdown fixtures  
**Version:** Batch 05 v1  

---

## Product contribution

This story creates a baseline classification for dynamic UI states that affect locator/action reliability.

## Architecture decision

Fixed:

- P0 detects/classifies dynamic state enough for recovery/trace
- full advanced handling can be future capability
- dynamic state classification is evidence, not automatic success
- unsupported/unknown state can route recovery/capability gap

## Dynamic state baseline

| State | P0 requirement |
|---|---|
| modal/dialog open | detect and include dialog context |
| dropdown/listbox open | detect if visible/options present |
| toast/alert | detect visible message where possible |
| loading/spinner | classify loading/unstable |
| navigation/page change | URL/title change |
| file picker/upload | capability gap unless supported |
| popup/new tab/iframe | capability gap/baseline detection |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM007-U-001 | Unit | modal open | modal state detected |
| DOM007-U-002 | Unit | dropdown open | options detected |
| DOM007-U-003 | Unit | toast visible | message detected |
| DOM007-U-004 | Unit | loading state | unstable warning |
| DOM007-U-005 | Unit | iframe present | unsupported/capability flag |
| DOM007-I-001 | Integration | action opens modal | observed dynamic state |

## Edge cases

- hidden modal in DOM
- dropdown portal outside container
- toast disappears quickly
- SPA route change
- browser permission prompt

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

First Codex task for DOM-007 should be read-only:

```text
Read DOM-007, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
