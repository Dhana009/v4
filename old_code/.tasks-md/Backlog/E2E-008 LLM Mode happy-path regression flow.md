# E2E-008 LLM Mode happy-path regression flow

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-006 E2E Harness and Real-world Fixtures  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** E2E-001, E2E-002, E2E-003, E2E-004, LLM-006, FE-004, BE-005, BE-006  
**Blocks:** MVP happy path validation  
**Version:** Batch 07 v1  

---

## Product contribution

This story validates the core Complete LLM Mode happy path end to end.

## Flow

```text
open fixture page
→ enter user intent
→ LLM planner mocked/recorded output
→ backend emits plan_ready
→ UI renders plan
→ user confirms
→ backend executes validated operation/assertion
→ backend records step
→ code_update appears
→ run_completed when valid
```

## Evidence required

- backend event sequence
- Shadow DOM screenshots
- browser action evidence
- recorded step payload
- code_update payload
- trace/artifact directory

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| E2E008-E-001 | E2E | click happy path | plan_ready→confirm→recorded→completed |
| E2E008-E-002 | E2E | visible assertion happy path | assertion recorded |
| E2E008-E-003 | E2E | exact text/code assertion | target/value correct |
| E2E008-E-004 | E2E | no action before confirm | no step_executing |

## Edge cases

- LLM output mocked vs live
- slow backend event
- locator validation fails
- UI stale plan

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

First Codex task for E2E-008 should be read-only:

```text
Read E2E-008, SOURCE-001, PLAN-002, PLAN-005, EPIC-006, EPIC-001 through EPIC-005, and required skills.
Do not edit code.
Inspect current test/harness/fixture ownership and report a narrow implementation path.
Do not implement until repo-inspection report is reviewed.
```
