# E2E-006 Weak WordPress-Elementor-style fixture coverage

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** E2E-004, DOM-005, DOM-010  
**Blocks:** weak DOM locator regressions, picker UI tests  
**Version:** Batch 07 v1  

---

## Product contribution

This story provides a weak DOM fixture that mimics WordPress/Elementor-style pages where semantic locators are often poor.

## Required fixture coverage

| Scenario | Required behavior |
|---|---|
| div/span CTA | ancestor candidate identifies clickable target |
| nested icon button | interactive ancestor preferred |
| duplicate CTA sections | section/card scoping |
| lead magnet form | labels/placeholders/validation |
| upload/permission gap | capability gap path |
| responsive layout | hook/locator stability |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E006-F-001 | Fixture | nested span CTA | ancestor button candidate |
| E2E006-F-002 | Fixture | duplicate CTA | ambiguity/scoping |
| E2E006-F-003 | Fixture | form fields | label/placeholder candidates |
| E2E006-F-004 | Fixture | upload unsupported | capability gap |

## Edge cases

- no ARIA roles
- generated classes
- repeated marketing sections
- hidden mobile/desktop variants

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current test runner and Playwright config
- current backend startup path
- current frontend/Shadow DOM startup path
- current WebSocket/event logging path
- current fixture/static server support
- current existing E2E/regression tests
- current CI scripts if any
- current artifact/output folders
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- tests would hit live external sites as a hard dependency
- event capture cannot be asserted
- Shadow DOM hooks are missing or unstable
- backend/frontend startup path is unclear
- LLM mocking/recording strategy is unclear
- failures do not produce artifacts/logs
- fixture data contains sensitive/private information
- implementation requires broad product rewrite instead of harness setup

---

## Codex execution summary

First Codex task for E2E-006 should be read-only:

```text
Read E2E-006, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
