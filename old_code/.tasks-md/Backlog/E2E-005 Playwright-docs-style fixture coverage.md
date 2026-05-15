# E2E-005 Playwright-docs-style fixture coverage

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** E2E-004, DOM-006, DOM-010  
**Blocks:** code block and docs-style locator regressions  
**Version:** Batch 07 v1  

---

## Product contribution

This story provides a docs-style fixture for nav/section/code-block/exact-text assertions.

## Required fixture coverage

| Scenario | Required behavior |
|---|---|
| docs navigation | role/name locator |
| code block | exact text/code assertion target |
| section heading | section-scoped text |
| tabs/sidebar | scoped navigation |
| repeated command text | disambiguation |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E005-F-001 | Fixture | docs page loads | ok |
| E2E005-F-002 | Fixture | code block candidate | text_block found |
| E2E005-F-003 | Fixture | exact command assertion | target/value separated |
| E2E005-F-004 | Fixture | repeated nav text | scoped locator |

## Edge cases

- whitespace-sensitive code
- duplicate section headings
- long code block
- sticky nav

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

First Codex task for E2E-005 should be read-only:

```text
Read E2E-005, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
