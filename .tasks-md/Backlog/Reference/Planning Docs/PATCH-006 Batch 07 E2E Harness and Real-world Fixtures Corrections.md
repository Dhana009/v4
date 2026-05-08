# PATCH-006 Batch 07 E2E Harness and Real-world Fixtures Corrections

**Type:** Planning Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** EPIC-006 and E2E-001 through E2E-010  
**Reason:** Codex Batch 07 review found the E2E harness strategy solid and repo-inspection-ready, but identified missing template completeness: source evidence tables, four-developer coordination, explicit fixture dependencies, startup sequencing, event correlation rules, Shadow DOM hook conventions, artifact bundle expectations, and CI/local execution details.  
**Decision:** Patch Batch 07. Do not regenerate. Do not start implementation from Batch 07 until this patch is applied.

---

## 1. Codex review result

Codex reviewed EPIC-006 and E2E-001 through E2E-010 using only Tasks.md planning files.

Result:

```text
Confidence: Medium
All E2E-001 through E2E-010 are ready for repo inspection.
No E2E story is ready for immediate implementation.
Final decision: Patch Batch 07.
```

Reason:

```text
The harness strategy is solid enough to prevent “unit tests pass but product breaks,”
but the batch is not template-complete and the dependency graph is under-explicit for later regression stories.
```

---

## 2. Patch goal

Patch objectives:

1. Add source evidence tables to E2E-002 through E2E-010.
2. Add four-developer coordination blocks to every E2E story.
3. Make fixture dependencies explicit for E2E-008, E2E-009, and E2E-010.
4. Add startup sequencing, health checks, retry, ports/env, cleanup, and CI/local mode rules.
5. Add backend event correlation and sequence assertion rules.
6. Add Shadow DOM hook lookup conventions.
7. Add fixture registry path/layout/sanitization/versioning/drift rules.
8. Add artifact bundle format, filenames, screenshots/traces/log rules.
9. Add CI/local/headed/headless execution expectations.
10. Tighten happy-path, negative-path, recording, code_update, and replay smoke flow evidence.

---

## 3. Source evidence table requirement for all E2E stories

Apply this to E2E-001 through E2E-010.

Every E2E story must include a source evidence table using this format:

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| PLAN-005 | Testing is part of story acceptance, not later QA. | E2E must provide acceptance evidence. | Story must define test proof and artifacts. |
| EPIC-001 | Backend owns runtime truth. | Tests must assert backend events, not only UI. | Story must capture/assert backend event truth. |
| EPIC-002 | Events/commands are typed. | E2E must use canonical payloads and command envelopes. | Story must validate event/command shapes. |
| EPIC-005 | Shadow DOM UI renders backend truth through stable hooks. | UI tests must use Shadow DOM hooks/accessibility. | Story must not test legacy overlay as primary UI. |
| EPIC-004 / DOM-010 | Realistic fixtures required. | Tests must use semantic and weak DOM fixtures. | Story must map fixtures to scenarios. |
| Handoff | Live flows exposed contract gaps tests missed. | Product-level flows are mandatory. | Story must test integration behavior, not isolated units only. |

Story-specific evidence rows:
- E2E-002: event stream capture is required to prove backend truth.
- E2E-003: stable frontend hooks are required to avoid brittle CSS/UI tests.
- E2E-004: fixture server/registry must avoid live-site CI dependency.
- E2E-008: happy path must prove plan_ready → confirm → execution → recording → code_update → run_completed.
- E2E-009: correction/clarification/recovery must prove false execution/completion is blocked.
- E2E-010: recording/code_update/replay smoke must prove backend-owned output and replay separation.

---

## 4. Four-developer coordination block to add to every E2E story

Add this standard section to each E2E story.

```markdown
## Four-developer coordination

| Developer | Relationship to this story |
|---|---|
| DEV-1 Backend | Provides backend startup, event stream, deterministic event payloads, command validation, and logs. |
| DEV-2 LLM/DOM | Provides mocked/recorded LLM outputs, DOM fixture expectations, and locator scenario expectations. |
| DEV-3 Frontend | Provides Shadow DOM hooks, UI state rendering, and command surfaces. |
| DEV-4 E2E | Primary owner. Builds harness, fixtures, assertions, artifacts, and regression flows. |

Story-specific coordination:
- DEV-1: <backend/event responsibility>
- DEV-2: <LLM/DOM fixture responsibility>
- DEV-3: <frontend/hook responsibility>
- DEV-4: <harness/assertion responsibility>
```

### Story-specific notes

#### E2E-001

```text
DEV-1 must document backend startup/health checks; DEV-3 must document frontend mount path; DEV-4 owns orchestration and teardown.
```

#### E2E-002

```text
DEV-1 owns event stream shape; DEV-4 owns capture/assertion helpers and event artifacts.
```

#### E2E-003

```text
DEV-3 owns stable hooks; DEV-4 owns Shadow DOM query helpers and UI assertion patterns.
```

#### E2E-004

```text
DEV-2/DEV-4 define fixture expectations; DEV-4 owns server/registry; DEV-1/3 consume fixtures for validation.
```

#### E2E-005

```text
DEV-2 defines docs/code-block expected DOM behavior; DEV-4 implements fixture assertions.
```

#### E2E-006

```text
DEV-2 defines weak DOM target expectations; DEV-4 ensures nested/duplicate/section-scoped cases exist.
```

#### E2E-007

```text
DEV-2 defines dynamic-state expectations; DEV-4 implements modal/dropdown/toast/loading fixture tests.
```

#### E2E-008

```text
DEV-1 provides event sequence; DEV-2 provides mocked planner output; DEV-3 provides plan UI hooks; DEV-4 proves happy path.
```

#### E2E-009

```text
DEV-1 provides rejection/recovery events; DEV-2 provides correction/recovery mocked outputs; DEV-3 provides recovery UI hooks; DEV-4 proves negative paths.
```

#### E2E-010

```text
DEV-1 provides recording/replay events; DEV-3 provides recorded/code/replay UI hooks; DEV-4 proves output and replay smoke.
```

---

## 5. E2E-001 startup/orchestration patch

Apply this to E2E-001.

### Startup sequencing

Required startup sequence:

```text
1. allocate run_id / artifact directory
2. start fixture server
3. start backend test process
4. wait for backend health check
5. start frontend/extension/Shadow DOM injection path
6. launch browser/context/page
7. attach backend event stream capture before user action
8. navigate to fixture page
9. verify Shadow DOM host is mounted
10. run test flow
11. collect artifacts
12. teardown browser/frontend/backend/fixture server
```

### Health checks

| Component | Required health signal |
|---|---|
| fixture server | fixture route returns expected page |
| backend | health endpoint/log/ready event |
| frontend | Shadow DOM root hook visible |
| event capture | listener attached and ready |
| browser | page created and navigated |

### Port/env handling

| Concern | Required behavior |
|---|---|
| ports | configurable or dynamically allocated |
| env vars | documented in story/repo inspection |
| timeouts | explicit default and override |
| retries | startup retry only where safe; no masking product failures |
| cleanup | always attempted in finally/afterEach |

### Tests to add

```markdown
| E2E001-I-005 | Integration | backend health timeout | clear startup failure artifact |
| E2E001-I-006 | Integration | fixture port collision | alternate port or clear failure |
| E2E001-I-007 | Integration | event capture not attached | test does not proceed |
| E2E001-I-008 | Integration | teardown after flow failure | no orphan processes |
```

---

## 6. E2E-002 event capture and correlation patch

Apply this to E2E-002.

### Correlation fields

Event assertion utilities must support filtering by:

| Field | Required use |
|---|---|
| run_id | primary run correlation |
| plan_id | plan review/correction |
| plan_version | stale plan assertions |
| step_id | step-specific assertions |
| operation_id | operation-specific assertions |
| command_id | command/rejection correlation |
| replay_run_id | replay assertions |
| event type | canonical event family |
| emitted_at/order | sequence assertions |

### Sequence-window behavior

| Situation | Required behavior |
|---|---|
| event emitted before listener attached | fail harness setup; do not silently miss |
| out-of-order event | clear failure with observed sequence |
| duplicate allowed event | policy-specific assertion |
| duplicate terminal event | fail or warn by policy |
| no-event assertion | time-boxed wait with artifact |
| reconnect | capture reconnect/session_state behavior explicitly |

### Artifact format

Event capture should save:

```text
events.ndjson
events.filtered.<test_id>.json
event_sequence_summary.txt
rejections.json
commands.json
```

Exact names can change after repo inspection, but format must be explicit.

### Tests to add

```markdown
| E2E002-U-004 | Unit | run_id filter | only matching run events |
| E2E002-U-005 | Unit | plan_version filter | stale/new plan separated |
| E2E002-U-006 | Unit | no-event assertion timeout | useful failure |
| E2E002-U-007 | Unit | observed sequence mismatch | reports expected vs actual |
```

---

## 7. E2E-003 Shadow DOM hook convention patch

Apply this to E2E-003.

### Hook lookup conventions

Harness must distinguish:

```text
AutoWorkbench Shadow DOM UI
target page DOM
legacy overlay if present
```

Suggested helpers:

| Helper | Required behavior |
|---|---|
| getAutoWorkbenchHost() | returns Shadow DOM host only |
| withinAutoWorkbench() | scopes locators inside Shadow DOM |
| withinTargetPage() | excludes AutoWorkbench host |
| getPanel(name) | panel by stable FE-009 hook |
| getCommandButton(name) | command button by stable role/name/hook |
| assertNoLegacyOverlayDependency() | ensures tests target Shadow DOM path |

### Required panel hooks

```text
aw-root
aw-panel-plan
aw-panel-recovery
aw-panel-recorded
aw-panel-code
aw-panel-trace
aw-picker
aw-status-run
aw-status-plan
aw-status-execution
```

### Tests to add

```markdown
| E2E003-I-004 | Integration | Shadow DOM vs target page | scoped helpers separate DOMs |
| E2E003-I-005 | Integration | legacy overlay also present | tests still target Shadow DOM |
| E2E003-I-006 | Integration | missing hook | clear harness failure |
```

---

## 8. E2E-004 fixture server and registry patch

Apply this to E2E-004.

### Fixture path/layout convention

Suggested layout:

```text
tests/fixtures/pages/
  docs-style/
  weak-wordpress/
  dynamic-ui/
  forms/
  cards-tables/
  capability-gaps/

tests/fixtures/registry.json
tests/fixtures/README.md
```

Exact paths may change after repo inspection.

### Registry-to-route mapping

Every fixture registry entry must map to a route:

| Field | Required |
|---|---|
| fixture_id | Yes |
| route_path | Yes |
| file_path | Yes |
| fixture_type | Yes |
| expected_dom_features | Yes |
| stories_covered | Yes |
| negative_cases | Yes |
| artifact_tags | Optional |

### Sanitization/versioning/drift

| Concern | Required behavior |
|---|---|
| sensitive data | no real private/user/customer data |
| versioning | fixture version or updated_at |
| drift detection | expected candidate/event checks fail if fixture changes |
| update workflow | optional live capture must be manual, not CI dependency |
| assets | local/static assets only where possible |

### Tests to add

```markdown
| E2E004-U-003 | Unit | registry route maps to file | valid |
| E2E004-U-004 | Unit | fixture has sensitive marker | rejected |
| E2E004-I-003 | Integration | every registry route loads | 200/ok |
| E2E004-I-004 | Integration | fixture drift baseline | expected feature check |
```

---

## 9. Fixture dependency patch for E2E-008 / E2E-009 / E2E-010

Apply this to E2E-008, E2E-009, and E2E-010.

### E2E-008 fixture dependencies

Add:

```text
Depends on E2E-005 for docs/code exact assertion happy path.
Depends on E2E-006 for weak DOM click/fill happy path.
May use E2E-007 only when happy path includes modal/dropdown behavior.
```

### E2E-009 fixture dependencies

Add:

```text
Depends on E2E-006 for locator ambiguity and weak DOM correction/recovery.
Depends on E2E-007 for dynamic UI recovery and modal/dropdown/toast cases.
May use E2E-005 for exact text correction and assertion target cases.
```

### E2E-010 fixture dependencies

Add:

```text
Depends on E2E-005 for code block / exact text recording/code_update.
Depends on E2E-006 for weak DOM recorded locator behavior.
Depends on E2E-007 for replay precondition and dynamic-state failure cases where relevant.
```

---

## 10. E2E-008 happy-path sequence patch

Apply this to E2E-008.

### Required event sequence

Minimum event sequence for happy-path test:

```text
run_started
plan_ready
confirmed command observed or confirmation accepted
step_validating
step_executing
step_recorded
code_update
run_completed
```

If implementation uses additional intermediate events, tests may allow them, but the above required events must appear in order where applicable.

### Mandatory artifacts

For each happy-path run:

```text
events.ndjson
commands.json
shadow-ui-before-confirm.png
shadow-ui-after-complete.png
target-page-before.png
target-page-after.png
recorded-step.json
code-update.json
trace-summary.txt
```

### Tests to add

```markdown
| E2E008-E-005 | E2E | required event sequence | all required events in order |
| E2E008-E-006 | E2E | mandatory artifacts | all files exist |
| E2E008-E-007 | E2E | no execution before confirm | no step_executing before confirmed |
```

---

## 11. E2E-009 negative-path sequence patch

Apply this to E2E-009.

### Required negative flow assertions

| Flow | Required event/UI proof |
|---|---|
| correction before confirm | old plan_version rejected; new plan_ready rendered |
| ambiguous intent | clarification_needed; no plan_ready until resolved |
| stale confirm | runtime_rejected with STALE_PLAN_VERSION |
| locator ambiguity | no step_executing; recovery/clarification shown |
| failed action | step_failed/recovery_needed; no run_completed |
| skip with reason | step_skipped; terminal policy explicit |
| stop run | stopped/session_state; no further execution |

### Mandatory artifacts

```text
events.ndjson
commands.json
rejections.json
recovery-or-clarification-ui.png
trace-summary.txt
```

### Tests to add

```markdown
| E2E009-E-006 | E2E | ambiguous intent does not plan | no plan_ready before clarification |
| E2E009-E-007 | E2E | failed action does not complete | no run_completed |
| E2E009-E-008 | E2E | stale confirm rejection | rejection code asserted |
```

---

## 12. E2E-010 recording/code/replay patch

Apply this to E2E-010.

### Required event sequence for recording/code

```text
step_executing
step_recorded
code_update
run_completed
```

Rules:

```text
code_update must not appear before step_recorded for the source step.
recorded child order must match confirmed plan order.
expected_outcome metadata must not become assertion target/value.
```

### Replay smoke sequence

Minimum replay sequence:

```text
replay_started
replay_result
```

Replay result must include:

```text
replay_run_id
mode
recorded_step_id or recorded_run_id
precondition_status
replay_status
evidence_ref when available
```

### Mandatory artifacts

```text
recorded-step.json
recorded-children.json
code-update.json
replay-result.json
events.ndjson
trace-summary.txt
```

### Tests to add

```markdown
| E2E010-E-006 | E2E | code_update after step_recorded | ordering asserted |
| E2E010-E-007 | E2E | replay_result identity | replay_run_id and target ids present |
| E2E010-E-008 | E2E | wrong-page replay | precondition failure artifact |
```

---

## 13. Artifact bundle standard

Apply this to EPIC-006 and all E2E stories.

### Artifact directory layout

Suggested format:

```text
artifacts/e2e/<timestamp>-<test_id>-<slug>/
  events.ndjson
  commands.json
  rejections.json
  backend.log
  frontend.log
  browser-console.log
  trace.zip
  screenshots/
    001-before.png
    002-after.png
  payloads/
    plan-ready.json
    recorded-step.json
    code-update.json
    replay-result.json
  summary.md
```

Exact paths may change after repo inspection, but every story must state what artifacts are required.

### When to capture

| Artifact | Required timing |
|---|---|
| events.ndjson | always |
| commands.json | always for command flows |
| screenshots | at key UI/page states and on failure |
| Playwright trace | on failure by default; optional always in debug mode |
| backend/frontend logs | always or failure-only by policy |
| payload JSON | for plan/recording/replay/code assertions |
| summary.md | always for failed runs; recommended always |

---

## 14. CI/local execution standard

Apply this to EPIC-006 and all E2E stories.

### Execution modes

| Mode | Required behavior |
|---|---|
| local headed | developer debugging |
| local headless | fast regression |
| CI headless | deterministic required path |
| debug artifacts | trace/screenshots/logs preserved |
| live external refresh | optional/manual only, not CI dependency |

### Required command shape

Exact commands are decided after repo inspection, but the harness must document:

```text
how to run all E2E tests
how to run one story/fixture test
how to run headed
how to preserve artifacts
how to mock/record LLM outputs
how to choose browser/project
```

### CI safeguards

```text
no mandatory live external site dependency
fixtures local and deterministic
timeouts explicit
artifacts uploaded/preserved where CI supports it
LLM API usage mocked/recorded for deterministic P0 unless explicitly testing live model route
```

---

## 15. Batch 07 patch acceptance criteria

Batch 07 is accepted after:

- E2E-002 through E2E-010 include source evidence tables.
- Every E2E story includes four-developer coordination.
- E2E-008/009/010 explicitly reference fixture dependencies.
- E2E-001 includes startup sequence, health checks, port/env handling, cleanup, and CI/local mode.
- E2E-002 includes event correlation fields, sequence-window behavior, and event artifact format.
- E2E-003 includes Shadow DOM hook lookup conventions.
- E2E-004 includes fixture path/layout, registry-to-route mapping, sanitization/versioning/drift rules.
- E2E-008 includes required happy-path event sequence and artifacts.
- E2E-009 includes required negative-path event/UI proof and artifacts.
- E2E-010 includes recording/code/replay sequence and replay identity rules.
- EPIC-006/all E2E stories include artifact bundle and CI/local execution standards.

After this patch:

```text
EPIC-006 = planning-ready.
E2E-001 through E2E-010 = ready for repo inspection.
E2E-001 through E2E-010 = not ready for immediate implementation.
```
