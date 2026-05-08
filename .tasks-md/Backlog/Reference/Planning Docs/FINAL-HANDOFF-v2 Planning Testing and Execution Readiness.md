# FINAL-HANDOFF-v2 Planning Testing and Execution Readiness

**Type:** Final Planning + Testing + Execution Readiness Handoff  
**Status:** Draft for review  
**Applies To:** AutoWorkbench / Playwright Automation Co-pilot / Complete LLM Mode  
**Audience:** Next thinking agent, Codex workers, DEV-1/DEV-2/DEV-3/DEV-4  
**Implementation Status:** Blocked until this handoff is reviewed and accepted  
**Version:** v2  

---

## 1. Executive status

AutoWorkbench planning has moved through three phases:

```text
Phase 1: Architecture planning
Phase 2: Testing doctrine and detailed test matrices
Phase 3: Execution readiness planning
```

Current status:

```text
Architecture backlog: complete
Architecture patches: complete through PATCH-009
Final handoff v1: complete
Testing doctrine: complete after PATCH-010
Detailed test matrices: complete after PATCH-011
Repo test mapping: completed once
Implementation: not started
Next required action: review FINAL-HANDOFF-v2
```

Important:

```text
Planning-ready does not mean implementation-ready.
Test-matrix-ready does not mean repo tests are implemented.
Repo test mapping found the full implementation path is still blocked.
Only the first backend/event test-first slice is currently considered safe after this handoff is accepted.
```

---

## 2. Source hierarchy

Use this source order when conflicts appear:

```text
1. PRD v2.3 modular docs
2. Complete LLM Mode architecture/spec documents
3. Frontend/UI spec
4. LLM Runtime Policy spec
5. Three-part handoff lessons
6. Tasks.md planning files and patches
7. Testing doctrine and matrices
8. Repo skills
9. Current implementation code
```

If current code conflicts with source architecture, treat current code as untrusted and report the gap.

---

## 3. Non-negotiable architecture truth model

The product must preserve this truth model:

```text
Backend = truth
LLM = reasoning/proposal
Frontend = display + command sender
DOM intelligence = candidate/context provider
Trace = evidence
Tests = enforcement layer
```

Forbidden:

```text
LLM owns runtime truth
frontend owns lifecycle truth
trace owns runtime truth
DOM candidate executes without backend/browser validation
recording/codegen is generated from LLM prose
expected_outcome becomes assertion target/value
P1/P2 behavior silently enters MVP
```

---

## 4. What has been planned

Architecture planning covered:

```text
EPIC-001 Backend Runtime Truth
EPIC-002 Typed Event Contract
EPIC-003 LLM Runtime Controller
EPIC-004 DOM and Locator Strategy
EPIC-005 Shadow DOM Frontend
EPIC-006 E2E Harness and Real-world Fixtures
EPIC-007 Complete LLM Mode MVP Flows
EPIC-008 Recording and Codegen
EPIC-009 Trace and Observability
EPIC-010 Advanced Capabilities and Backlog Governance
```

The planning backlog includes:

```text
BE stories
EVENT stories
LLM stories
DOM stories
FE stories
E2E stories
MVP stories
REC stories
TRACE stories
GOV stories
```

Each major story generally contains:

```text
product contribution
source evidence
architecture boundary
schema/contract
dependency map
four-developer coordination
test matrix
artifact expectations
repo-inspection requirement
stop conditions
```

---

## 5. Testing doctrine and matrix inventory

Testing artifacts created:

```text
TEST-DOCTRINE-001 Risk-Based TDD Doctrine
TEST-MERGE-001 Four Developer TDD Merge Checkpoint Plan
TEST-BE-001 Backend Runtime Truth Test Strategy
TEST-LLM-DOM-001 LLM Runtime and DOM Intelligence Test Strategy
TEST-FE-001 Shadow DOM Frontend Test Strategy
TEST-E2E-001 Cross-layer E2E and Fixture Test Strategy
TEST-HANDOFF-001 How to Use Test Matrices Before Implementation
TEST-MATRIX-BE-001 Backend Runtime Truth Test Cases
TEST-MATRIX-EVENT-001 Typed Event Command Contract Test Cases
TEST-MATRIX-LLM-DOM-001 LLM Runtime and DOM Intelligence Test Cases
TEST-MATRIX-FE-001 Shadow DOM Frontend Test Cases
TEST-MATRIX-E2E-001 Cross-layer Product E2E Test Cases
TEST-MATRIX-MVP-001 MVP Acceptance Gate Test Cases
PATCH-010 Batch 12 Testing Doctrine Corrections
PATCH-011 Batch 13 Detailed Test Matrix Corrections
```

Testing rule:

```text
If it is not testable, do not build it.
If it is in the PRD and affects runtime/product behavior, it must become a test property.
If it affects runtime truth, it must have unit + integration + regression coverage.
```

---

## 6. Mandatory P0 test properties

These are non-negotiable test properties:

```text
1. No execution before confirmation.
2. Backend rejects stale plan_version.
3. LLM cannot emit runtime truth.
4. Frontend cannot infer lifecycle truth.
5. Trace cannot become runtime truth.
6. Every command has typed validation/rejection.
7. Every event has typed envelope and causal order.
8. Locator specialist output cannot execute without backend/browser validation.
9. Ambiguous locator blocks execution.
10. Recovery open blocks run_completed.
11. Recording requires execution evidence.
12. code_update follows step_recorded.
13. expected_outcome stays metadata only.
14. visible assertion does not become click.
15. exact_text assertion keeps expected_value.
16. Correction cannot silently drop/reorder children.
17. Multi-step strict cursor prevents contamination.
18. Unsupported capability becomes typed gap.
19. Every UI failure state gives a next safe action.
20. Every failed E2E produces artifacts.
```

---

## 7. Repo test mapping result

A repo test mapping was completed after Batch 12/13 patches.

Result:

```text
Full test mapping: blocked
First safe slice identified: backend/event contract test-first slice
Implementation: still blocked until this final handoff is accepted
```

Existing strengths:

```text
Backend/runtime pytest tests exist.
Event contract tests exist.
Replay/save/completion tests exist.
Four E2E flow tests exist.
E2E harness exists.
Some static fixtures exist.
```

Major gaps:

```text
No repo-local CI/coverage config.
No dedicated frontend test harness.
No dedicated trace/export harness.
E2E harness does not emit required artifact set:
  events.ndjson
  commands.json
  rejections.json
  summary.md
  test-result.json
  manifest.json
  redaction report
Fixture coverage is too narrow.
Current matrices need PATCH-011 source-rule/invariant mapping applied.
```

---

## 8. Current blockers

Implementation is blocked by:

```text
FINAL-HANDOFF-v2 not yet reviewed/accepted.
No enforced repo coverage/CI config.
Trace/export/redaction harness missing.
Dedicated frontend test harness missing.
Fixture suite incomplete.
Full source-rule/matrix-to-test mapping not implemented in repo.
```

Only after this handoff is accepted may the first test-first slice begin.

---

## 9. Four-developer model

### DEV-1: Backend Runtime + Events + Recording

Owns:

```text
backend runtime truth
event/command contracts
command validation
execution contract
recovery lifecycle
recording/codegen
completion guard
replay smoke
backend trace
```

First safe focus:

```text
backend/event contract tests
backend restart/isolation/late-event tests
command/rejection compatibility tests
```

Do not start with:

```text
broad agent.py refactor
replay repair
frontend changes
DOM/picker changes
```

---

### DEV-2: LLM Runtime + DOM Intelligence

Owns:

```text
LLM Runtime Controller
purpose registry
tool phase gating
schema validation
DOM extraction
DOM compression/context selection
locator specialist
main LLM vs specialist handoff
DOM fixture-driven tests
```

Blocked until:

```text
fixture/harness direction is clearer
backend event/command contract is stable enough
```

Do not start with:

```text
prompt changes without tests
extra model calls
broad locator refactor without fixtures/tests
```

---

### DEV-3: Shadow DOM Frontend

Owns:

```text
Shadow DOM host
typed event store
command dispatcher
plan/recovery UI
recorded/code panel
picker UI
trace panel
no-deadlock states
accessibility/test hooks
legacy overlay migration audit
```

Blocked until:

```text
event/command contract is stable
frontend harness approach is decided
```

Do not start with:

```text
large UI redesign
legacy overlay patching without migration plan
local lifecycle state shortcuts
```

---

### DEV-4: E2E Harness + Fixtures + Evidence

Owns:

```text
test harness
fixture server
event capture
artifact export
redaction checks
MVP gate
CI/coverage integration
cross-layer E2E proof
```

Should start early because all other streams need evidence.

First focus:

```text
test command/coverage/CI discovery
artifact harness gap plan
E2E fixture-flow mapping
```

---

## 10. Proposed PR / merge sequence

Do not use large long-running branches. Use small checkpoint PRs.

### PR-0: Repo testing infrastructure readiness

Owner: DEV-4  
Purpose:

```text
define test commands
coverage command
artifact output location
CI/local execution model
```

No product behavior change.

---

### PR-1: Backend/event contract tests

Owner: DEV-1  
Purpose:

```text
add/strengthen event-command-rejection tests
backend isolation/restart/late-event test coverage
```

Tests first. Production implementation only later.

---

### PR-2: Backend/event contract implementation

Owner: DEV-1  
Purpose:

```text
make PR-1 tests pass with narrow contract changes
```

No broad refactor.

---

### PR-3: E2E artifact harness baseline

Owner: DEV-4  
Purpose:

```text
events/commands/rejections/summary/test-result artifact baseline
```

---

### PR-4: LLM Runtime Controller tests

Owner: DEV-2  
Purpose:

```text
purpose registry
tool gating
schema retry/fail-closed
prompt/context assembly tests
```

---

### PR-5: DOM fixture and candidate tests

Owner: DEV-2 + DEV-4  
Purpose:

```text
local fixtures for weak DOM, docs/code, hidden variants, dynamic UI
DOM extraction/candidate tests
```

---

### PR-6: Frontend event/command shell tests

Owner: DEV-3  
Purpose:

```text
event store
command dispatcher
truth boundary
no-deadlock basics
```

---

### PR-7+: MVP flow slices

Owners: all, coordinated by DEV-4  
Order:

```text
lifecycle smoke
simple click
visible assertion
exact text assertion
correction
clarification
locator ambiguity/recovery
multi-step strict cursor
recording/code_update
trace/artifact/redaction
```

---

## 11. PR evidence checklist

Every PR must include:

```text
source story/test IDs
matrix test IDs covered
tests added/updated
positive tests
negative tests
boundary/edge tests if relevant
regression tests if touching known failure area
commands run
coverage result if applicable
E2E artifacts if product flow changed
architecture invariant statement
files changed
known gaps / next PR
```

A PR must not only say:

```text
Implemented feature X.
```

It must say:

```text
Protected source rule Y and invariant Z through test IDs A/B/C.
```

---

## 12. Merge blockers

Block merge if:

```text
tests are missing
negative tests are missing for validator/state work
coverage cannot be measured for changed deterministic modules
frontend owns lifecycle truth
LLM owns runtime truth
trace owns runtime truth
recording/codegen is not evidence-backed
event/command payload is untyped
error state has no next action
E2E artifact missing for product-flow change
source-rule mapping missing
```

---

## 13. Test execution model

### Local focused tests

Run before commit:

```text
changed unit tests
changed contract tests
small integration tests
```

### PR required tests

Run before merge:

```text
all affected unit tests
all affected contract tests
affected integration tests
affected E2E if product flow changed
coverage for changed deterministic modules
```

### Full regression

Run before MVP gate:

```text
backend regression
event/command regression
LLM/DOM regression
frontend regression
E2E fixture regression
artifact/redaction regression
MVP acceptance gate
```

---

## 14. First safe test-first slice

Repo mapping identified this as first safe slice:

```text
backend/event contract slice
```

Scope:

```text
event envelope contract tests
command envelope/rejection tests
legacy/canonical compatibility tests
backend restart/isolation/late-event tests
deterministic schema-version behavior
```

Likely test files:

```text
tests/test_event_contracts.py
tests/test_ws_reconnect_grace.py
tests/test_replay_one.py
tests/test_replay_all.py
tests/test_save_spec.py
tests/test_completion_guard.py
tests/test_recovery_scope_guard.py
```

Still do not begin this slice until FINAL-HANDOFF-v2 is reviewed and accepted.

---

## 15. What not to do next

Do not:

```text
start broad implementation
refactor agent.py
touch frontend Shadow DOM migration
change DOM/locator logic
add replay repair
add session restore
add advanced observed outcome detection
patch prompts without tests
write code before selected tests are mapped
```

---

## 16. Next action after this handoff

Correct next process:

```text
1. Paste FINAL-HANDOFF-v2 into Tasks.md.
2. Ask Codex to review FINAL-HANDOFF-v2.
3. If Codex says patch, patch it.
4. If accepted, choose first test-first slice.
5. Ask Codex to create tests only for that slice.
6. Review test diff/evidence.
7. Then implement narrowly to pass tests.
```

---

## 17. Codex review prompt for this handoff

Use this after pasting the file:

```text
MODE:
Final handoff review only.
Do not inspect product code.
Do not edit files.
Do not implement.

TASK:
Review FINAL-HANDOFF-v2 Planning Testing and Execution Readiness.

GOAL:
Tell us whether this handoff is complete enough to start test-first implementation planning.

CHECK:
1. Does it accurately summarize architecture planning?
2. Does it include testing doctrine and matrix status?
3. Does it reflect repo test mapping result?
4. Does it clearly state current blockers?
5. Does it define four-developer responsibilities?
6. Does it define PR/merge sequence?
7. Does it define evidence checklist and merge blockers?
8. Does it avoid starting implementation too early?
9. Is the first safe slice reasonable?
10. What is missing before starting test-first implementation?

FINAL DECISION:
- Accept FINAL-HANDOFF-v2
- Patch FINAL-HANDOFF-v2
- Regenerate FINAL-HANDOFF-v2
```

---

## 18. Final status

```text
Planning closure: nearly complete
Testing closure: nearly complete
Execution readiness: pending review of this handoff
Implementation: blocked
Next step: Codex review of FINAL-HANDOFF-v2
```
