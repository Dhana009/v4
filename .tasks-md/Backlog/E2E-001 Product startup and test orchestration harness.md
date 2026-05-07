# E2E-001 Product startup and test orchestration harness

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-006, FE-001, BE-001  
**Blocks:** all E2E stories  
**Version:** Batch 07 v1  

---

## Product contribution

This story creates the single reliable way to start the product under test and run product-level regression flows.

## Source evidence table

| Source | Extracted rule | Story impact |
|---|---|---|
| PLAN-005 | E2E proves full product behavior | orchestrate backend/frontend/browser |
| EPIC-001 | backend owns truth | backend must run in test mode |
| EPIC-005 | Shadow DOM UI is frontend target | browser must load UI host |
| EPIC-006 | failed runs produce artifacts | harness saves evidence |

## Architecture decision

Fixed:

- harness starts backend, frontend/extension/overlay entry, browser, and fixture server as needed
- tests should be runnable locally
- startup health checks are explicit
- artifacts are stored per run
- harness should not depend on live external sites

## Orchestration contract

| Component | Required behavior |
|---|---|
| backend | start/health check/stop |
| frontend | inject/mount Shadow DOM UI |
| browser | launch/context/page |
| fixture server | start/serve fixture pages |
| event capture | attach before flow starts |
| artifact directory | created per run |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E001-I-001 | Integration | start backend | healthy |
| E2E001-I-002 | Integration | start fixture server | fixture URL works |
| E2E001-I-003 | Integration | launch browser and UI | Shadow host visible |
| E2E001-I-004 | Integration | teardown | no orphan process |
| E2E001-E-001 | E2E | smoke startup flow | artifacts created |

## Edge cases

- backend port already in use
- browser launch failure
- frontend injection failure
- fixture server unavailable
- teardown after failed test

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

First Codex task for E2E-001 should be read-only:

```text
Read E2E-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
