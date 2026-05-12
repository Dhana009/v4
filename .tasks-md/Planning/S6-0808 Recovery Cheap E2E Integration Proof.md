# S6-0808 — Recovery Cheap E2E / Integration Proof

## Story ID
S6-0808

## Objective
Prove recovery end-to-end with local fixtures and fake LLM before paid E2E.

## Required flows

```
1. locator count > 1 → recovery/ambiguity → user choice → continue
2. hidden element → deterministic recovery (scroll) → success
3. assertion timeout → recovery_needed → user correction → continue
4. unsupported capability → capability_gap → no fake success
```

## What it contains

- Local fixture pages with recovery scenarios
- Fake LLM (recovery_diagnoser mock) for repair proposals
- Integration test suite covering all 4 flows
- No paid E2E, no real LLM, no browser
- Cheap validation before paid E2E (S6-0809)

## What it must NOT contain

- Paid LLM (that's paid E2E)
- Real browser (use fixtures)
- Frontend UI (that's app)
- Broad agent.py changes

## Tests first

### Integration tests

Flow 1: Locator ambiguity

```
- Page has 2 buttons with same text
- Locator returns 2 matches
- failure_classifier → locator_matches_multiple
- Deterministic recovery suggests both candidates
- User chooses first candidate
- Resume executes first button correctly
```

Flow 2: Hidden element

```
- Target element hidden
- Action fails with element_hidden
- Deterministic recovery scrolls/focuses
- Element becomes visible
- Resume succeeds without LLM
```

Flow 3: Assertion timeout

```
- Assertion waits for text that takes 3 seconds
- Timeout occurs
- failure_classifier → assertion_timeout
- recovery_diagnoser suggests wait-longer repair
- Repair validated and executed
- Assertion succeeds after repair
```

Flow 4: Unsupported capability

```
- Plan includes unsupported action
- Capability registry returns unsupported
- recovery_diagnoser cannot propose repair
- capability_gap emitted
- No fake success recorded
```

### Cheap E2E acceptance

- No run_completed while recovery open
- step_recorded emitted only after validated success
- code_update emitted after step_recorded
- Artifacts include failure classification and tried recoveries
- All 4 flows end in either success or explicit capability_gap/stop

## Dependencies

- Requires: All of Cluster 8 (S6-0801 through S6-0807)
- Blocks: S6-0809 (Regression), paid E2E

## Acceptance criteria

- All 4 required flows passing locally
- Fake LLM recovery_diagnoser mock complete
- Integration tests use local fixtures only
- No paid E2E, no real LLM, no browser
- 95% coverage on integration test suite
- Artifacts validated with recovery evidence
- Ready for paid E2E after regression guard passes

## Notes

- Cheap E2E proves recovery without expense
- Fixture pages can be simple HTML; only need to trigger recovery scenarios
- Fake LLM recovery_diagnoser returns valid repair proposals for cheap flows
- Design for cost: all validation happens before paid E2E
