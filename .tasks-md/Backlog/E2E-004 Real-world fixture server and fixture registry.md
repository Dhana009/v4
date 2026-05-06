# E2E-004 Real-world fixture server and fixture registry

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-006, DOM-010  
**Blocks:** E2E-005, E2E-006, E2E-007, all DOM locator tests  
**Version:** Batch 07 v1  

---

## Product contribution

This story creates the local fixture server and registry used by DOM/locator/product regressions.

## Architecture decision

Fixed:

- fixtures are local/stable/sanitized
- live external sites are optional update sources, not CI dependencies
- registry describes expected DOM features and test expectations
- fixture server can run with product harness

## Fixture registry schema

| Field | Required |
|---|---|
| fixture_id | Yes |
| path/url | Yes |
| fixture_type | Yes |
| stories_covered | Yes |
| DOM_features | Yes |
| expected_candidates | Yes |
| expected_events | Optional |
| negative_cases | Yes |
| data_sensitivity | Yes |
| update_source | Optional |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E004-U-001 | Unit | registry load | valid |
| E2E004-U-002 | Unit | missing fixture file | clear failure |
| E2E004-I-001 | Integration | fixture server start | serves pages |
| E2E004-I-002 | Integration | all registry paths | load successfully |

## Edge cases

- fixture drift
- huge fixture
- sensitive data
- missing assets
- route collision

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

First Codex task for E2E-004 should be read-only:

```text
Read E2E-004, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
