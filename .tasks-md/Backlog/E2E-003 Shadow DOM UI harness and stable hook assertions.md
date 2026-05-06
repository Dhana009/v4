# E2E-003 Shadow DOM UI harness and stable hook assertions

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-006, FE-001, FE-002, FE-009  
**Blocks:** frontend UI E2E flows  
**Version:** Batch 07 v1  

---

## Product contribution

This story lets tests verify the actual Shadow DOM frontend through stable hooks and accessible roles.

## Architecture decision

Fixed:

- tests target Shadow DOM host, not legacy overlay
- stable hooks from FE-009 are preferred
- UI assertions are paired with backend event assertions for lifecycle truth
- UI helper methods live in harness, not product runtime

## UI harness helpers

| Helper | Purpose |
|---|---|
| getShadowRoot() | locate AutoWorkbench UI |
| getPanel(name) | locate panel |
| assertRunStatus(status) | UI status assertion |
| clickCommand(name) | send UI command |
| enterPrompt(text) | user intent input |
| assertPlanVisible(plan_id?) | plan review |
| assertRecoveryVisible() | recovery UI |
| assertRecordedStep() | recorded panel |
| assertCodeContains() | code panel |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E003-U-001 | Unit | hook locator map | selectors valid |
| E2E003-I-001 | Integration | shadow root visible | host found |
| E2E003-I-002 | Integration | plan panel render | UI reflects event |
| E2E003-I-003 | Integration | command click | command envelope sent |

## Edge cases

- Shadow host remounted
- panel hidden/collapsed
- duplicate hooks
- legacy overlay also present

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

First Codex task for E2E-003 should be read-only:

```text
Read E2E-003, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
