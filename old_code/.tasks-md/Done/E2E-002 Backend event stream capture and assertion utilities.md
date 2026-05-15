# E2E-002 Backend event stream capture and assertion utilities

Status: Done  
Sprint: Sprint 0  


**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** EPIC-006, EVENT-001, EVENT-003, BE-002  
**Blocks:** all event-backed E2E flows  
**Version:** Batch 07 v1  

---

## Product contribution

This story lets tests verify backend truth by capturing and asserting typed events.

## Architecture decision

Fixed:

- event capture starts before user action
- assertions use canonical event names and identity fields
- UI-only success is insufficient for lifecycle tests
- event artifacts saved on failure

## Event assertion utilities

| Utility | Purpose |
|---|---|
| wait_for_event(type, filter) | wait for canonical event |
| assert_sequence([...]) | assert ordered event chain |
| assert_no_event(type) | prove forbidden event did not happen |
| collect_events(run_id) | artifact output |
| assert_rejection(code) | negative flow assertions |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E002-U-001 | Unit | event filter | matches run_id/type |
| E2E002-U-002 | Unit | missing expected event | clear failure |
| E2E002-U-003 | Unit | assert no event | passes/fails correctly |
| E2E002-I-001 | Integration | capture plan_ready | event saved |
| E2E002-I-002 | Integration | rejection captured | rejection code asserted |

## Edge cases

- duplicate events
- out-of-order events
- missing run_id
- WebSocket reconnect
- event emitted before listener attaches

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

First Codex task for E2E-002 should be read-only:

```text
Read E2E-002, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```


## Sprint 0 note

This item is part of the completed foundation baseline. If later audits reveal missing live-product wiring, track that as a new Sprint 2+ integration story rather than reopening this foundation story.
