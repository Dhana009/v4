# DEVELOPER-EXECUTION-PLAN-001 Four Developer Branch Checkpoint and Merge Plan

**Type:** Developer Execution Plan  
**Status:** Draft for review  
**Priority:** P0  
**Applies To:** DEV-1 Backend, DEV-2 LLM/DOM, DEV-3 Frontend, DEV-4 E2E/Evidence  
**Depends On:** FINAL-HANDOFF-v2, PATCH-012, TEST-DOCTRINE-001, PATCH-010, TEST-HANDOFF-001, PATCH-011  
**Implementation Status:** Blocked until this plan is reviewed and accepted  

---

## 1. Purpose

This document converts the completed architecture and testing planning into a practical four-developer working model.

It defines:

```text
who starts where
which branch each developer uses
what each developer can and cannot touch
what checkpoint must pass before merge
when to raise MR
what evidence must be attached
how branches rebase after merge
what blocks progress
```

This document does not authorize implementation by itself.

---

## 2. Core operating rule

```text
No test mapping → no test writing.
No tests → no implementation.
No negative tests → no merge.
No artifact evidence → no product-flow acceptance.
No source-rule mapping → no merge.
```

Every developer must work from:

```text
source rule
→ selected matrix rows
→ repo test mapping
→ tests first
→ narrow implementation
→ evidence
→ MR
```

---

## 3. Global branch discipline

### Branch naming

Use short-lived feature branches:

```text
dev4/test-infra-artifact-readiness
dev1/backend-event-contract-test-mapping
dev1/backend-event-contract-tests
dev1/backend-event-contract-implementation
dev2/llm-dom-test-mapping
dev2/llm-runtime-controller-tests
dev2/dom-fixture-candidate-tests
dev3/frontend-test-harness-mapping
dev3/frontend-event-command-shell-tests
dev4/e2e-artifact-harness-baseline
dev4/e2e-fixture-matrix-baseline
```

### Branch rules

```text
1. One branch = one small slice.
2. Test-mapping branches do not modify production code.
3. Test-only branches do not modify production code unless explicitly approved.
4. Implementation branches must only make selected tests pass.
5. No branch mixes backend, frontend, DOM fixtures, trace exporter, and LLM changes in one MR.
6. Every branch lists selected matrix rows.
7. Every branch lists allowed and forbidden files.
8. Every branch stops if it touches out-of-scope layers.
```

---

## 4. Rebase rule

After every merge into main:

```text
1. All active branches must rebase from main.
2. Rerun affected tests.
3. Resolve contract drift immediately.
4. Do not continue broad work on stale base.
5. If rebase changes event/command/schema behavior, affected developers must rerun contract tests.
```

If rebase creates conflicts in shared contracts:

```text
stop
summarize conflict
identify source rule
ask planning brain for decision
do not guess
```

---

## 5. Developer ownership overview

| Developer | Owns | Starts with | Must not start with |
|---|---|---|---|
| DEV-1 | Backend runtime, events, command validation, recording/codegen, completion, replay smoke | Backend/event contract test mapping | broad agent.py refactor, replay repair |
| DEV-2 | LLM Runtime Controller, DOM extraction/compression, locator specialist, schema/tool policy | LLM/DOM repo test mapping | prompt changes, locator refactor, extra model calls |
| DEV-3 | Shadow DOM frontend, event store, command dispatcher, UI states, picker/trace UI | frontend harness/test mapping | UI redesign, local lifecycle shortcuts |
| DEV-4 | E2E harness, fixtures, artifacts, CI/coverage, MVP gate evidence | test infra/artifact readiness | full trace exporter before scope accepted |

---

## 6. DEV-1 Backend/Event execution plan

### First branch

```text
dev1/backend-event-contract-test-mapping
```

### First task

Focused mapping only:

```text
Map backend/event selected matrix rows to existing repo tests and proposed test files.
Do not modify code.
Do not create tests yet.
```

### Board note

BE-001 through BE-004 have now been decomposed into measurable subtasks and moved to Planning on the DEV-1 board. Leave BE-005 through BE-012 untouched for this batch.

### Board note

BE-005 through BE-008 have now been decomposed into measurable subtasks and moved to Planning on the DEV-1 board. Leave BE-009 through BE-012 untouched for this batch.

### Board note

BE-001 through BE-008 audit children were moved through In Progress and closed as Done on the DEV-1 board after focused backend contract verification. Leave BE-009 through BE-012 untouched for the next batch.

### Board note

BE-001 through BE-012 have now been moved to Done on the DEV-1 board. The planned DEV-1 backend P0 scope is complete.

### Board note

Next step is full backend verification and coverage review before any merge/push decision.

### Board note

Deferred items remain outside the done scope, including broad replay repair, full session restore UX, frontend/LLM/DOM/E2E/trace work, and advanced browser capabilities.

### Selected first-slice matrix areas

```text
EVENT-C-001 through EVENT-C-006
EVENT-CMD-C-001 through EVENT-CMD-C-006
EVENT-SEQ-001 through EVENT-SEQ-007
EVENT-COMP rows from PATCH-011
BE-ISO rows from PATCH-011
BE-RESTART rows from PATCH-011
BE-SNAP rows from PATCH-011
BE-LATE rows from PATCH-011
BE-PROC rows from PATCH-011
```

### Likely test files

```text
tests/test_event_contracts.py
tests/test_ws_reconnect_grace.py
tests/test_replay_one.py
tests/test_replay_all.py
tests/test_save_spec.py
tests/test_completion_guard.py
tests/test_recovery_scope_guard.py
tests/test_backend_restart_isolation.py if new file is justified
```

### Allowed files for mapping branch

```text
No file modifications.
Read only:
.tasks-md/**
tests/**
```

### Allowed files for later test branch

```text
tests/test_event_contracts.py
tests/test_ws_reconnect_grace.py
tests/test_replay_one.py
tests/test_replay_all.py
tests/test_save_spec.py
tests/test_completion_guard.py
tests/test_recovery_scope_guard.py
new backend test files only if justified
```

### Forbidden files until implementation branch

```text
agent.py
runtime/**
server.py
browser.py
locator.py
frontend/**
frontend/dist/**
.tasks-md/**
```

### MR checkpoint

Raise MR after:

```text
selected matrix rows mapped
existing/missing tests identified
proposed test files listed
commands to run identified
stop conditions listed
```

For later test branch, raise MR after:

```text
tests added/updated
tests run
expected failing tests documented
no production code modified
```

---

## 7. DEV-2 LLM/DOM execution plan

### First branch

```text
dev2/llm-dom-test-mapping
```

### First task

Mapping only:

```text
Map LLM/DOM matrix rows to current repo tests, fixtures, and missing harnesses.
Do not implement.
Do not edit prompts.
Do not change locator logic.
```

### Matrix areas

```text
LLM-C / LLM-N / LLM-R controller rows
LLM-CTX rows from PATCH-011
LLM-CONF rows from PATCH-011
DOM extraction rows
DOM-SHADOW rows from PATCH-011
DOM-TIE rows from PATCH-011
DOM-DRIFT rows from PATCH-011
HANDOFF main LLM vs locator specialist rows
```

### Likely current test files

```text
tests/test_context_manager.py
tests/test_skill_loading.py
tests/test_tool_registry.py
tests/test_plan_model.py
tests/test_plan_correction.py
tests/test_assertion_flow.py
tests/e2e/**
```

### Likely future files

```text
tests/test_llm_controller.py
tests/test_dom_locator.py
tests/test_dom_context_assembly.py
tests/test_locator_specialist_contract.py
tests/e2e/fixtures/test_app/weak_dom.html
tests/e2e/fixtures/test_app/hidden_variants.html
tests/e2e/fixtures/test_app/dynamic_ui.html
```

### Allowed files for mapping branch

```text
No file modifications.
Read only:
.tasks-md/**
tests/**
runtime/context_manager.py if needed for mapping only
runtime/model_router.py if needed for mapping only
```

### Forbidden until explicit implementation slice

```text
prompt changes
model routing changes
locator ranking changes
DOM extraction changes
browser.py
locator.py
agent.py
frontend/**
```

### MR checkpoint

Raise MR after:

```text
LLM/DOM selected matrix rows mapped
missing fixture requirements documented
current test coverage classified
blocked rows identified
first safe DEV-2 test slice proposed
```

DEV-2 must not start implementation until DEV-1 contracts and DEV-4 fixture/evidence direction are stable enough.

---

## 8. DEV-3 Frontend execution plan

### First branch

```text
dev3/frontend-test-harness-mapping
```

### First task

Mapping only:

```text
Map frontend matrix rows to existing E2E tests and identify missing frontend harness approach.
Do not implement Shadow DOM.
Do not change frontend source.
```

### Matrix areas

```text
FE-P truth rendering rows
FE-C command dispatcher rows
FE-E no-deadlock rows
FE-PICK picker rows
FE-TRACE trace rows
FE-A11Y accessibility rows
FE-WS reconnect rows from PATCH-011
FE-SHADOW isolation rows from PATCH-011
FE-RACE stale confirm/correction rows from PATCH-011
FE-LEGACY migration rows from PATCH-011
```

### Likely current coverage

```text
tests/e2e/test_basic_click_flow.py
tests/e2e/test_visible_assertion_flow.py
tests/e2e/test_exact_text_assertion_flow.py
tests/e2e/test_correction_assert_then_click_flow.py
tests/test_event_contracts.py
tests/test_recorded_step_model.py
tests/test_code_update.py
```

### Likely future test files

```text
frontend component/store tests if test runner is added
tests/e2e/frontend_state_tests.py if only E2E path is available
tests/e2e/test_frontend_command_dispatch.py
tests/e2e/test_frontend_no_deadlock_states.py
```

### Allowed files for mapping branch

```text
No file modifications.
Read only:
.tasks-md/**
tests/**
frontend/package.json
frontend/src/**
```

### Forbidden until explicit implementation slice

```text
Shadow DOM implementation
legacy overlay rewrite
frontend local state shortcuts
frontend/dist/**
backend runtime changes
```

### MR checkpoint

Raise MR after:

```text
frontend matrix rows mapped
frontend harness options listed
recommended first frontend test slice proposed
blocked rows identified
no source files modified
```

DEV-3 must not implement before event/command contracts are stable.

---

## 9. DEV-4 E2E/Fixture/Evidence execution plan

### First branch

```text
dev4/test-infra-artifact-readiness
```

### First task

Readiness discovery and plan:

```text
Inspect current test commands, E2E harness, artifact output, fixture coverage, CI/coverage support.
Do not implement product behavior.
```

### Current checkpoint

```text
Branch: dev4/test-infra-artifact-readiness
Worktree: /Users/apple/personal/agent-v4-dev-4

MR-0A status: complete, discovery/mapping only, no files changed

MR-0B status: complete and committed as fadbe98
MR-0B files changed:
  tests/e2e/harness.py
  tests/test_e2e_harness.py
MR-0B evidence:
  manifest.json baseline
  test-result.json baseline
  5 passed for tests/test_e2e_harness.py
  41 passed, 2 xfailed for backend/event focused suite

MR-2A status: complete, mapping only, no files changed

MR-2B status: complete and committed as b6a2f89
MR-2B files changed:
  tests/e2e/harness.py
  tests/test_e2e_harness.py
MR-2B evidence:
  backend.log
  frontend.log
  browser-console.log
  summary.md
  file_hashes in manifest
  optional-absence notes
  7 passed for tests/test_e2e_harness.py
  41 passed, 2 xfailed for backend/event focused suite

MR-2B forbidden:
  no events.ndjson
  no commands.json
  no rejections.json
  no redaction
  no trace export
  no backend/runtime/frontend/fixture/CI changes

Dirty state:
  AGENTS.md may remain dirty as local metadata; do not stage it.
```

### DEV-4 blocker slice

```text
Selected story: E2E-001 Product startup and test orchestration harness
Story status: Planned
Selected subtask: E2E-001A remove socket.bind-based free-port probing from tests/e2e/harness.py and add focused regression coverage in tests/test_e2e_harness.py
Selected subtask status: Blocked
Blocker note: DEV-1 is blocked by the DEV-4 E2E socket bind issue at tests/e2e/harness.py:61
Exact reason: the local sandbox denies loopback socket binds for both the harness and the fixture static server, so the four E2E tests fail during startup with PermissionError [Errno 1] Operation not permitted.
Scope:
  tests/e2e/harness.py
  tests/test_e2e_harness.py
  .tasks-md/Planning/DEVELOPER-EXECUTION-PLAN-001 Four Developer Branch Checkpoint and Merge Plan.md
Forbidden:
  agent.py
  server.py
  runtime/**
  frontend/**
  fixtures/**
  AGENTS.md
  .DS_Store
  CI/config
Verification:
  python -m pytest tests/test_e2e_harness.py -q
  python -m pytest tests/e2e/test_basic_click_flow.py tests/e2e/test_correction_assert_then_click_flow.py tests/e2e/test_exact_text_assertion_flow.py tests/e2e/test_visible_assertion_flow.py -q
  python -m pytest tests -q if the environment allows local socket allocation
Safe next action:
  rerun the same E2E suite in an environment that allows local loopback binds, or attach the harness to an already-running local backend/static server that does not require new socket creation
```

### E2E-002 status

```text
Selected story: E2E-002 Backend event stream capture and assertion utilities
Story status: Done
Completed subtask: event helper and evidence utilities complete
Completed subtask status: Done
Verification: python -m py_compile tests/e2e/harness.py tests/test_e2e_harness.py
Verification: python -m pytest tests/test_e2e_harness.py -q -> 30 passed
Completion note: collect_events, wait_for_event, assert_sequence, assert_no_event, event_evidence metadata, and artifact emission helpers are complete.
```

### TRACE-010 slice

```text
Selected story: TRACE-010 Observability regression and redaction policy
Story status: Done
Why next: TRACE-009 artifact export is complete, and TRACE-010C closed the remaining no-secret artifact metadata redaction gap for trace/export safety.
Phase: TRACE-010C complete; residual no-secret artifact metadata edge cases closed.
Scope:
  .tasks-md/Planning/TRACE-010 Observability regression and redaction policy.md
  .tasks-md/Planning/DEVELOPER-EXECUTION-PLAN-001 Four Developer Branch Checkpoint and Merge Plan.md
  tests/test_e2e_harness.py
Allowed files:
  .tasks-md/Planning/TRACE-010 Observability regression and redaction policy.md
  .tasks-md/Planning/DEVELOPER-EXECUTION-PLAN-001 Four Developer Branch Checkpoint and Merge Plan.md
  tests/test_e2e_harness.py
Forbidden files:
  agent.py
  server.py
  runtime/**
  frontend/**
  fixtures/**
  AGENTS.md
  .DS_Store
Test plan:
  TRACE-010B-001 redaction report artifact emission
  TRACE-010B-002 redaction report schema contract
  TRACE-010B-003 no-secret summary and metadata
  TRACE-010B-004 optional absence note rewrite
  TRACE-010B-005 missing redaction report gate
First test-first step:
  add failing tests for redaction-report.json baseline and no-secret artifact metadata only
TRACE-010B result:
  `tests/e2e/harness.py` now writes `redaction-report.json`, redacts the known fake token/OTP/email/phone/password values from summary/result/manifest metadata, rewrites the optional absence note when the report is present, and keeps the missing-report evidence gate failing.
  Verification: `python -m py_compile tests/e2e/harness.py tests/test_e2e_harness.py`
  Verification: `python -m pytest tests/test_e2e_harness.py -q` -> 35 passed
TRACE-010C scope:
  residual no-secret artifact metadata edge cases only
TRACE-010C result:
  `tests/e2e/harness.py` now recursively redacts nested metadata and sensitive URL query params in failure-context.json, failure.txt, summary event evidence, and manifest/test-result event_evidence without leaking raw secrets.
  Verification: `python -m py_compile tests/e2e/harness.py tests/test_e2e_harness.py`
  Verification: `python -m pytest tests/test_e2e_harness.py -q` -> 39 passed
TRACE-010D result:
  Covered by TRACE-010B/010C implementation; no code change needed.
TRACE-010E result:
  Verification and evidence capture complete; `python -m py_compile tests/e2e/harness.py tests/test_e2e_harness.py` and `python -m pytest tests/test_e2e_harness.py -q` passed.
Deferred gaps:
  live browser E2E blocked by localhost bind environment
  trace.ndjson deferred
  fixtures deferred
  CI/coverage deferred
Stop conditions:
  redaction policy remains unclear
  implementation would touch runtime or frontend truth
  redaction report would become a second source of truth
  evidence would require socket-bound browser startup in the blocked environment
```

### Matrix areas

```text
E2E-P / E2E-N / E2E-B / E2E-E rows
E2E-ISO rows from PATCH-011
E2E-FLAKE rows from PATCH-011
E2E-ART rows from PATCH-011
TRACE matrix rows from PATCH-011
MVP-GATE rows
```

### Likely files

```text
tests/e2e/harness.py
tests/e2e/test_basic_click_flow.py
tests/e2e/test_visible_assertion_flow.py
tests/e2e/test_exact_text_assertion_flow.py
tests/e2e/test_correction_assert_then_click_flow.py
tests/e2e/fixtures/test_app/**
frontend/package.json
```

### Allowed files for discovery branch

```text
No file modifications unless explicitly approved.
Read only:
.tasks-md/**
tests/**
frontend/package.json
repo config files
```

### Later allowed files for PR-0 implementation

```text
test command scripts/config
coverage config
E2E harness artifact output
artifact directory conventions
```

### Forbidden until explicit slice

```text
product runtime logic
frontend UI implementation
LLM/DOM implementation
trace exporter beyond accepted PR-0 scope
new broad fixture suite before fixture matrix is finalized
```

### MR checkpoint

Raise MR after:

```text
canonical test commands identified or proposed
coverage support identified/proposed
artifact output gap documented
fixture coverage gap documented
CI/local tier recommendation produced
```

If minimal config changes are approved, split into:

```text
PR-0A discovery/report
PR-0B minimal test command/coverage/artifact config
```

---

## 10. Shared PR sequence

### MR-0A: Test infrastructure discovery/report

Owner: DEV-4  
Type: mapping/discovery  
Status: complete in `fadbe98`; discovery only; no files changed  
Production code: no  
Merge when:

```text
test commands known/proposed
coverage status known
artifact gaps known
fixture gaps known
CI/local tier plan proposed
```

---

### DEV-1 board index

Owner: DEV-1  
Branch: `dev1/backend-isolation-contract-tests`  
Main baseline: `908f4d0`

The detailed DEV-1 board now lives in folder-state files:

| State | File | Current meaning |
|---|---|---|
| Done | [`Done/DEV-1 Backend Runtime and Recording Done.md`](../Done/DEV-1%20Backend%20Runtime%20and%20Recording%20Done.md) | completed work split into merged-to-main and branch-only done items |
| In Progress | [`Inprogress/DEV-1 Recording Codegen Truth Implementation.md`](../Inprogress/DEV-1%20Recording%20Codegen%20Truth%20Implementation.md) | the only active DEV-1 implementation slice |
| Planning / Pending | [`Planning/DEV-1 Planned Backend Contract Work.md`](./DEV-1%20Planned%20Backend%20Contract%20Work.md) | picked-but-not-started backend slices |
| Testing | [`Testing/DEV-1 Backend Contract Testing Queue.md`](../Testing/DEV-1%20Backend%20Contract%20Testing%20Queue.md) | no active DEV-1 testing item right now |
| Backlog / Deferred | [`Backlog/DEV-1 Deferred Backend and Cross-Lane Work.md`](../Backlog/DEV-1%20Deferred%20Backend%20and%20Cross-Lane%20Work.md) | out-of-scope and cross-lane deferred work |

Current board summary:
- Done: backend/event foundation, MR-1B through MR-1E, recovery isolation, snapshot/archive loader, late-event/late-command/process-boundary contracts, recording/codegen contract tests.
- In Progress: recording/codegen truth implementation.
- Planning: replay smoke, restart/session-load, reconnect/session_state extension, broader save/load/replay evidence checks.
- Backlog: replay repair, full session restore UX, cross-lane frontend/LLM-DOM/E2E/trace/capabilities work.

Current verification note:
- The focused backend contract suite and the recording/codegen contract slice have been verified previously; see the folder-state files for the exact item-level results.

---

### MR-2A: E2E artifact harness mapping

Owner: DEV-4  
Type: mapping  
Status: complete; mapping only; no files changed  
Merge when:

```text
artifact outputs mapped
minimal artifact baseline selected
trace/export scope separated from first baseline
```

---

### MR-2B: E2E artifact baseline

Owner: DEV-4  
Type: test infrastructure  
Status: recommended next scope  
Merge when:

```text
events/commands/rejections/summary/test-result baseline exists or approved subset exists
affected E2E passes
artifact retention rule documented
```

---

### MR-3A: LLM/DOM mapping

Owner: DEV-2  
Type: mapping  
Merge when:

```text
LLM/DOM matrix rows mapped
fixture needs documented
first safe LLM test slice proposed
blocked rows identified
```

Status note:
- MR-3A mapping completed on `dev2/llm-dom-test-mapping`.
- Source docs read, including the three Complete LLM Mode specs.
- DEV-2 backlog items identified: `DOM-001..DOM-010` and `LLM-001..LLM-010`.
- DEV-2 planned scope remains the full `DOM-001..DOM-010` plus `LLM-001..LLM-010` backlog set; this board has no separate Planned lane, so backlog is the planned state.
- First In Progress slice is `LLM-001` through `LLM-004`.
- MR-3B tests-only started on `dev2/llm-dom-test-mapping`; active slice is `LLM-001` through `LLM-004`.
- MR-3C finalized on `dev2/llm-dom-test-mapping`; `runtime/llm_runtime_controller.py` now satisfies the 7 contract tests for the LLM Runtime Controller foundation.
- LLM-001 through LLM-004 moved to Done after final verification.
- MR-3D tests-only started on `dev2/llm-dom-test-mapping`; active scope is `LLM-005` through `LLM-007`.
- Tests-only phase; no implementation yet.
- MR-3D implementation completed for `LLM-005` through `LLM-007`.
- Focused verification passed: `tests/test_llm_planning_contracts.py` now passes `12/12`; nearby runtime/helper suites passed `37/37`.
- No merge to main yet.
- Next planned slice is `LLM-008` through `LLM-010`.
- MR-3E implementation completed for `LLM-008` through `LLM-010`.
- Focused verification passed: `tests/test_llm_planning_contracts.py` + `tests/test_llm_specialist_contracts.py` + `tests/test_llm_runtime_controller_contract.py` passed `28/28`; nearby runtime/helper suites passed `30/30`.
- Optional coverage tool was unavailable in this environment (`--cov` not recognized by the installed pytest).
- No merge to main yet.
- LLM-005 through LLM-010 are finalized and moved to Done after verification.
- Next approved DEV-2 slice is `DOM-001` through `DOM-005`.
- DOM-001 through DOM-005 finalized and moved to Done on `dev2/llm-dom-test-mapping`; focused verification passed with `tests/test_dom_locator_contracts.py` at `8/8`; no implementation changes in this finalize step; no merge to main yet.
- DOM-006 through DOM-010 started as the next Inprogress slice.
- DOM-006 through DOM-010 tests-first slice started on `dev2/llm-dom-test-mapping`; advanced contract tests are being added before implementation, and missing seams are marked xfail with explicit reasons.
- DOM-006 through DOM-010 implementation completed on `dev2/llm-dom-test-mapping`; advanced DOM contract tests now pass, no merge to main yet, no push.
- DEV-2 LLM + DOM planned scope completed on branch; LLM-001 through LLM-010 Done and DOM-001 through DOM-010 Done.
- Final verification passed; no merge to main; no push in this task; AGENTS.md left unstaged.
- Shared/blocked rows: `DOM-010` with DEV-4 fixtures.
- Next checkpoint: proceed to the next approved DEV-2 slice after board review.
- MR-3C implementation is complete.
- Test-first work for the LLM Runtime Controller foundation slice is complete.

---

### MR-4A: Frontend harness mapping

Owner: DEV-3  
Type: mapping  
Merge when:

```text
frontend matrix rows mapped
test harness approach recommended
blocked rows identified
dependency on event contract documented
```

---

### MR-5+: Implementation slices

Allowed only after relevant mapping + tests exist.

---

## 11. MR evidence checklist

Every MR must include:

```text
branch name
developer owner
source rule IDs
matrix test IDs
files changed
files intentionally not touched
tests added/updated
positive/negative/boundary/edge/regression coverage
commands run
coverage result if available
artifacts if E2E/product flow affected
architecture invariant statement
known gaps
next recommended MR
```

Mapping-only MRs must include:

```text
mapping table
existing tests
missing tests
proposed files
blocked rows
first safe next slice
```

---

## 12. Shared contract failure handoff

If a shared contract test fails:

| Failing area | Primary owner | Collaborators |
|---|---|---|
| backend event envelope | DEV-1 | DEV-3, DEV-4 |
| frontend command envelope | DEV-3 | DEV-1, DEV-4 |
| LLM schema output | DEV-2 | DEV-1 |
| DOM candidate schema | DEV-2 | DEV-4 |
| recording/code_update payload | DEV-1 | DEV-3, DEV-4 |
| trace/artifact export | DEV-4 | DEV-1, DEV-3 |
| MVP E2E flow | DEV-4 | all impacted owners |

Required failure handoff:

```text
failing test ID
source rule
observed payload/event/UI state
expected contract
suspected owner
artifact/log path
root cause classification
next test/fix plan
```

---

## 13. Global stop conditions

Stop if:

```text
implementation starts before mapping
tests are skipped because they are hard
developer touches forbidden files
branch expands beyond selected slice
frontend starts owning lifecycle state
LLM starts owning runtime truth
trace starts owning runtime truth
recording/codegen is not evidence-backed
event/command schema is unclear
coverage cannot be measured for changed deterministic modules
E2E artifacts cannot be captured for product-flow change
```

---

## 14. Current next action

After this plan is pasted:

```text
1. Ask Codex to review this developer execution plan.
2. Patch if Codex says patch.
3. After accepted, create final new-chat handoff.
4. Move to new chat.
5. In new chat, start with MR-0A or MR-1A mapping only, not implementation.
```

---

## 15. Final status

```text
Architecture planning: done
Testing doctrine/matrices: done with patches
Execution readiness: pending review of this plan
Implementation: blocked
Next: Codex review of DEVELOPER-EXECUTION-PLAN-001
```
