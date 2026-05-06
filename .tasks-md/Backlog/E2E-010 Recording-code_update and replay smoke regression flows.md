# E2E-010 Recording-code_update and replay smoke regression flows

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** E2E-001, E2E-002, E2E-003, BE-009, BE-010, BE-012, FE-006, EVENT-006, EVENT-008  
**Blocks:** recording/code/replay acceptance  
**Version:** Batch 07 v1  

---

## Product contribution

This story proves the output side of the product: backend-owned recording, deterministic code_update, and backend-owned replay smoke.

## Required flows

| Flow | Expected |
|---|---|
| successful execution records parent/children | step_recorded payload |
| code_update after recording | code panel updates |
| expected_outcome metadata | displayed but not assertion source |
| replay one step | replay_started/replay_result |
| replay wrong page | precondition failure |
| replay during active execution | rejected or isolated by policy |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E010-E-001 | E2E | recorded child order | matches confirmed plan |
| E2E010-E-002 | E2E | code_update after recording | code visible |
| E2E010-E-003 | E2E | expected_outcome metadata | no leakage |
| E2E010-E-004 | E2E | replay step smoke | replay result |
| E2E010-E-005 | E2E | replay wrong page | precondition failure |

## Edge cases

- code_update before recording
- failed child after success
- duplicate recorded step
- replay missing recorded child

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

First Codex task for E2E-010 should be read-only:

```text
Read E2E-010, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
