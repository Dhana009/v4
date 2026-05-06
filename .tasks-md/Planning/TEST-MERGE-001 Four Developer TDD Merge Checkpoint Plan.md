# TEST-MERGE-001 Four Developer TDD Merge Checkpoint Plan

**Type:** Merge / TDD Governance  
**Status:** Planning  
**Priority:** P0  
**Owner:** Planning Brain + DEV-4 Evidence Governance  

## 1. Core merge rule

```text
No test → no code.
No negative test → no merge.
No artifact for E2E → no acceptance.
No architecture invariant proof → no merge.
```

## 2. Developer ownership

### DEV-1 Backend Runtime + Recording
```text
state-machine transitions
command validation/rejection
event envelope/order
execution cursor
recovery lifecycle
recording/codegen
completion guard
replay smoke
backend trace/redaction
```

### DEV-2 LLM Runtime + DOM/Locator
```text
LLM purpose registry
tool phase gating
schema validation/retry/fail-closed
DOM extraction/compression
locator candidate/ranking
locator specialist handoff
planner/correction/recovery outputs
token budget
real-world DOM fixtures
```

### DEV-3 Shadow DOM Frontend
```text
event store
command dispatcher
plan review UI
clarification/recovery UI
recorded/code panel
picker UI
trace panel
no-deadlock states
accessibility/test hooks
```

### DEV-4 E2E Harness + Fixtures + Evidence
```text
startup harness
event capture
fixture server/registry
cross-layer E2E
MVP gate
artifact bundle
redaction checks
CI/local execution
```

## 3. Checkpoint sequence

### Checkpoint 0: Repo inspection
```text
map current code to planning
identify current tests
identify gaps
confirm first implementation slice
```

### Checkpoint 1: Test skeletons
Each developer adds or identifies tests first. Merge blocked if tests are absent.

### Checkpoint 2: Contract/state tests pass
Backend/event/LLM/frontend contracts must pass before broad feature work.

### Checkpoint 3: Layer implementation
Implementation must be narrow and match the tests.

### Checkpoint 4: Cross-layer integration
Run focused integration tests for affected layer.

### Checkpoint 5: E2E evidence
Run affected E2E and capture artifacts.

### Checkpoint 6: Review gate
Reviewer checks:
```text
source rule mapping
positive/negative/boundary/edge coverage
coverage threshold
artifact evidence
no architecture violation
```

## 4. Branch rules

Suggested branches:
```text
dev1/backend-runtime-contracts
dev2/llm-dom-intelligence
dev3/shadow-dom-frontend
dev4/e2e-fixtures-evidence
```

Merge order:
```text
DEV-4 harness skeleton
DEV-1 backend/event contracts
DEV-2 LLM/DOM contracts
DEV-3 frontend event/command shell
DEV-4 cross-layer E2E
MVP flow branches
recording/codegen branches
trace/observability branches
```

## 5. PR evidence checklist

Every implementation PR must include:
```text
source story/test reference
tests added/updated
positive cases covered
negative cases covered
boundary/edge cases covered where relevant
coverage result
commands run
E2E artifacts if product flow affected
known regressions checked
architecture invariant statement
remaining gaps
```

## 6. Merge blockers

Block merge if:
```text
tests were added after implementation with no clear TDD reason
coverage below threshold for changed deterministic modules
frontend owns lifecycle truth
LLM owns runtime truth
trace owns runtime truth
recording/codegen not evidence-backed
unsupported behavior not typed as gap
error state has no next action
E2E artifacts missing
```
