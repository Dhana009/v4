# E2E-007 Modal-dropdown-toast and dynamic-state fixture coverage

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** E2E-004, DOM-007, EVENT-007  
**Blocks:** dynamic UI and recovery tests  
**Version:** Batch 07 v1  

---

## Product contribution

This story provides fixture coverage for dynamic UI states that often break browser automation.

## Required fixture coverage

| Scenario | Required behavior |
|---|---|
| modal/dialog | dialog context detected |
| dropdown/listbox | options detected, including portal dropdown |
| toast/alert | transient message evidence |
| loading/spinner | unstable state |
| SPA navigation | page-change evidence |
| iframe/popup boundary | capability gap or unsupported state |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E007-F-001 | Fixture | modal opens | dynamic state detected |
| E2E007-F-002 | Fixture | portal dropdown | option context detected |
| E2E007-F-003 | Fixture | transient toast | evidence captured |
| E2E007-F-004 | Fixture | loading state | wait/recovery path |
| E2E007-F-005 | Fixture | iframe target | capability gap |

## Edge cases

- toast disappears before assertion
- dropdown detached from trigger
- modal hidden in DOM
- route change invalidates locator

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

First Codex task for E2E-007 should be read-only:

```text
Read E2E-007, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
