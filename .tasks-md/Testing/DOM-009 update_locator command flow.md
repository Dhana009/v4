# DOM-009 update_locator command flow

**Type:** Story  
**Status:** Testing
**Priority:** P0  
**Epic:** EPIC-004 DOM and Locator Strategy  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EVENT-002, EVENT-003, DOM-004, DOM-008, BE-003  
**Blocks:** recovery, replay repair later, frontend locator update UI  
**Version:** Batch 05 v1  

---

## Product contribution

This story defines a safe command flow to update or replace a locator candidate during recovery or future replay repair.

## Architecture decision

Fixed:

- update_locator is a command request, not direct mutation
- backend validates run/step/operation identity
- candidate must validate in browser before acceptance
- old locator history/evidence preserved
- P0 supports baseline update; robust replay repair is P1

## Command contract

| Field | Required | Meaning |
|---|---|---|
| type | Yes | update_locator |
| command_id | Yes | idempotency |
| run_id | Conditional | active/replay run |
| step_id | Yes | parent |
| operation_id | Yes | child |
| locator_candidate | Conditional | proposed locator |
| user_hint | Optional | human context |
| reason | Yes | why updating |
| source | Yes | frontend/user/system |

## Flow

```text
update_locator command
→ command validation
→ locator validation
→ accept/reject
→ event/rejection emitted
→ execution/replay may retry only after accept
```

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| DOM009-C-001 | Contract | valid update_locator | accepted for validation |
| DOM009-C-002 | Contract | missing operation_id | rejected |
| DOM009-U-001 | Unit | candidate validates unique | accepted |
| DOM009-U-002 | Unit | candidate multiple | rejected/ambiguity |
| DOM009-U-003 | Unit | stale step | rejected |
| DOM009-I-001 | Integration | recovery locator update | retry allowed after accept |

## Edge cases

- update during active execution
- replay locator update
- locator valid but wrong semantic target
- user hint only, no selector
- old locator history missing

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

First Codex task for DOM-009 should be read-only:

```text
Read DOM-009, SOURCE-001, PLAN-002, PLAN-005, EPIC-004, LLM-008, BE-006, EVENT-005, and required skills.
Do not edit code.
Inspect current DOM/locator ownership and report narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
