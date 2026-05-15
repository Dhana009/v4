# E2E-009 Correction-clarification-recovery regression flows

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** E2E-001, E2E-002, E2E-003, FE-004, FE-005, BE-007, BE-008, LLM-005, LLM-007, LLM-009  
**Blocks:** negative path validation  
**Version:** Batch 07 v1  

---

## Product contribution

This story proves the product handles non-happy-path LLM Mode flows safely.

## Required flows

| Flow | Expected |
|---|---|
| correction before confirm | old plan rejected; revised plan shown |
| ambiguous intent | clarification_needed; no plan guessing |
| stale confirm | runtime_rejected |
| locator ambiguity | recovery/clarification; no execution |
| failed action | recovery_needed; no run_completed |
| skip with reason | step_skipped and terminal policy |
| stop run | stopped, no further execution |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E009-E-001 | E2E | correction assert-then-click | revised plan executes |
| E2E009-E-002 | E2E | clarification missing target | clarification UI |
| E2E009-E-003 | E2E | stale confirm | rejection UI/event |
| E2E009-E-004 | E2E | failed locator | recovery_needed |
| E2E009-E-005 | E2E | stop from recovery | stopped state |

## Edge cases

- duplicate correction
- invalid LLM diff twice
- recovery option stale
- stop during execution

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

First Codex task for E2E-009 should be read-only:

```text
Read E2E-009, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
