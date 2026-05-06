# PATCH-010 Batch 12 Testing Doctrine Corrections

**Type:** Testing Doctrine Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** TEST-DOCTRINE-001, TEST-MERGE-001, TEST-BE-001, TEST-LLM-DOM-001, TEST-FE-001, TEST-E2E-001  
**Reason:** Codex Batch 12 review accepted the doctrine direction with high confidence but found operational gaps that must be patched before detailed matrices are treated as reliable.  
**Decision:** Patch Batch 12. Do not regenerate. Do not use Batch 13 detailed matrices until this patch is applied.

---

## 1. Codex review result

```text
Confidence: High
Final decision: Patch Batch 12
```

Codex found Batch 12 strong enough as the base for test matrices, but not yet ready to accept because it needs clearer source-rule mapping, CI/coverage enforcement, backend restart/isolation coverage, Shadow DOM/race coverage, E2E cleanup/flake policy, and trace/observability evidence expectations.

---

## 2. Patch goal

This patch adds:

```text
1. Canonical source-rule → test-property template
2. CI tiering and coverage enforcement rules
3. Coverage exemption policy
4. Backend restart / multi-run / late-event / corrupted snapshot coverage
5. LLM/DOM Shadow DOM extraction, candidate tie-break, stale snapshot, and prompt/context assembly coverage
6. Frontend reconnect, Shadow DOM isolation, keyboard/focus, stale race, and legacy-overlay migration coverage
7. E2E fixture-to-flow matrix, cleanup/isolation, flake policy, and artifact retention
8. Trace/observability strategy coverage
9. Shared contract failure handoff rules across four developers
10. Escape hatch for PRD items that are non-runtime, non-testable, or documentation-only
```

---

## 3. TEST-DOCTRINE-001 source-rule mapping patch

Add this section.

### Canonical source-rule → test-property template

Every test matrix row must map back to a source rule.

Use this format:

| Field | Required | Meaning |
|---|---:|---|
| Source ID | Yes | PRD/story/spec reference, e.g. `EPIC-001`, `EVENT-002`, `LLM-004` |
| Source extract | Yes | Short exact/paraphrased rule being tested |
| Architecture invariant | Yes | Non-negotiable rule derived from source |
| Test property | Yes | What must always be true |
| Failure prevented | Yes | What bug/drift this test prevents |
| Test IDs | Yes | Unit/integration/E2E IDs that prove it |
| Owner | Yes | DEV-1/2/3/4 |
| Evidence | Yes | Expected logs/events/artifacts/coverage |

Example:

```text
Source ID: BE-006
Source extract: Confirmed plan children are the execution contract.
Architecture invariant: Backend validates every operation against the confirmed cursor.
Test property: Wrong step_id or operation_id is rejected before browser execution.
Failure prevented: Cross-step contamination.
Test IDs: BE-N-006, BE-N-007, E2E-P-008.
Owner: DEV-1 + DEV-4.
Evidence: runtime_rejected payload + event stream.
```

### Non-testable source item escape hatch

The rule “if it is in the PRD, it must become a test property” means runtime/product requirements.

Use this exception policy:

| Source item type | Handling |
|---|---|
| Runtime/product behavior | Must become test property |
| Architecture invariant | Must become test property |
| Contract/schema rule | Must become contract test |
| Documentation-only note | May become checklist item |
| Future/P1/P2 concept | Classified and tested as typed gap if encountered |
| Non-testable research idea | Mark Research; no implementation until testability defined |

Forbidden:

```text
Implementing non-testable runtime behavior.
Using “hard to test” as reason to skip P0 tests.
```

---

## 4. TEST-DOCTRINE-001 CI and coverage enforcement patch

Add this section.

### CI tiers

| Tier | Runs when | Includes | Purpose |
|---|---|---|---|
| Tier 0 local focused | before commit | changed unit/contract tests | fast TDD loop |
| Tier 1 PR required | every PR | unit + contract + affected integration | merge safety |
| Tier 2 PR impacted E2E | product-flow PRs | affected E2E + artifacts | cross-layer proof |
| Tier 3 nightly/full | scheduled/main | full E2E, fixtures, redaction, flake tracking | regression proof |
| Tier 4 manual/live | explicit only | optional live site capture/checks | exploratory evidence, not CI dependency |

### Coverage thresholds

| Area | Threshold |
|---|---:|
| New/changed backend deterministic modules | 95% line + branch coverage for validators/reducers |
| New/changed deterministic LLM/DOM controller modules | 95% line coverage |
| Event/command/LLM schemas | 100% valid/invalid schema coverage |
| Known regressions touched by PR | 100% covered |
| Frontend stores/dispatchers | 95% line coverage |
| E2E MVP gate | 100% required flow coverage before MVP pass |

### Generated/excluded code policy

Coverage excludes only:

```text
generated files
vendored files
build artifacts
static fixture HTML/CSS unless intentionally unit-tested
type-only declarations if applicable
```

Every exclusion must be listed in PR evidence.

### Coverage failure rule

```text
If changed deterministic code drops below threshold, merge is blocked.
If threshold cannot be measured, stop and add measurement before implementation.
```

---

## 5. TEST-BE-001 backend missing coverage patch

Add these sections.

### Restart / restore / isolation coverage

Required backend tests:

| Test area | Required cases |
|---|---|
| Multi-run isolation | old run event cannot mutate current run |
| Backend restart | reconnect after restart does not fake active truth |
| Corrupted snapshot | load fails with typed rejection/gap |
| Session restore boundary | supported fields restored; unsupported fields typed gap |
| Late events | late duplicate events after recovery/reconnect cannot corrupt state |
| Cross-process boundary | persisted/archive data has schema validation before use |

### Additional backend test properties

```text
run_id is mandatory for run-scoped mutation
plan_id/version cannot cross runs
recorded_step_id cannot be reused across runs unless explicitly archived
late step_recorded after run_completed is rejected/diagnostic
late recovery_needed after run_completed is rejected/diagnostic
corrupted replay archive cannot execute
```

### Add mandatory backend regressions

```text
16. Old run event cannot mutate current run.
17. Corrupted snapshot/load fails safely.
18. Late duplicate event after recovery/reconnect cannot corrupt state.
19. Reconnect after backend restart cannot recreate runtime truth from frontend cache.
20. Cross-run command_id reuse cannot mutate wrong run.
```

---

## 6. TEST-LLM-DOM-001 missing coverage patch

Add these sections.

### Shadow DOM-aware extraction and ranking

LLM/DOM tests must cover:

```text
open Shadow DOM host traversal if product UI is target
closed/unavailable Shadow DOM typed limitation
shadow-root boundaries are represented safely
candidate ranking does not accidentally mix app overlay controls with target page controls
frontend Shadow DOM controls are excluded from target-page locator candidates unless explicitly testing AutoWorkbench UI
```

### Candidate tie-break determinism

When multiple equivalent candidates exist, tests must assert deterministic behavior.

Required tie-break metadata:

```text
candidate_id
visibility
role/name/text
ancestor/section context
DOM order or explicit ranking score
confidence
reason
ambiguity status
```

Expected:

```text
If tie is unsafe, route ask_user/recovery.
If tie-break is deterministic and safe, expose reason and backend validation still required.
```

### Stale snapshot vs execution drift

Add tests for:

```text
DOM snapshot taken before navigation
element removed before execution
candidate visible during planning, hidden during execution
SPA route changes DOM after plan_ready
backend/browser validation catches stale target
recovery_needed or ask_user emitted
```

### Prompt/context assembly contract

Every LLM purpose must define:

```text
allowed source context
forbidden context
DOM budget
history budget
skills allowed
tools allowed
trace snippets allowed
redaction requirements
overflow behavior
```

Tests must check:

```text
main planner does not get full raw DOM unnecessarily
locator specialist does not get full chat history
recovery diagnoser gets failure evidence but not unrelated DOM
prompt/context assembly respects source hierarchy and skill precedence
```

### Explicit confidence thresholds

Required policy:

| Confidence | Behavior |
|---|---|
| high + backend/browser valid | may proceed after confirmation |
| medium | ask_user or validate with stronger evidence |
| low | ask_user/recovery/more context |
| unknown | no execution |

---

## 7. TEST-FE-001 missing coverage patch

Add these sections.

### WebSocket reconnect/disconnect UX

Required tests:

```text
backend disconnected shows visible disconnected state
pending command during disconnect does not show success
reconnect refreshes from backend/session state, not local truth
rejected command after reconnect is shown clearly
user has stop/retry/export diagnostic where safe
```

### Shadow root isolation

Required tests:

```text
AutoWorkbench Shadow DOM root exists
styles do not leak into target page
target page styles do not break panel basics
target page locator extraction excludes AutoWorkbench UI controls
Shadow DOM host unmount/remount does not corrupt backend state
```

### Keyboard/focus and accessibility

Required tests:

```text
confirm/correction/recovery actions keyboard accessible
focus moves to recovery/clarification when emitted
modal/panel traps focus only when appropriate
screen-reader names exist for critical actions
long panel scroll does not hide action buttons permanently
```

### Stale confirm/correction race

Required tests:

```text
confirm button disabled/pending during correction submit
stale plan_version rejection renders clear message
correction response for old plan does not overwrite current plan UI
double submit correction handled safely
```

### Legacy overlay migration assertions

If legacy overlay remains live, tests must explicitly prove:

```text
legacy overlay compatibility path does not own runtime truth
legacy overlay and Shadow DOM do not both mutate state
legacy event normalization does not create fake lifecycle success
migration audit lists which path is active
```

---

## 8. TEST-E2E-001 missing coverage patch

Add these sections.

### Fixture-to-flow matrix

Every fixture must map to the flows it proves.

| Fixture class | Required flows |
|---|---|
| clean semantic | lifecycle, simple click, visible assert |
| weak div/span | locator ambiguity, ancestor candidate, duplicate CTA |
| docs/code-block | exact_text/code assertion, tabs, multi-step |
| form-heavy | fill/select/validation, required fields |
| cards/table rows | scoped row/card targeting |
| modal/dialog | recovery/dynamic blocking |
| portal dropdown | dynamic option selection/recovery |
| toast/loading/spinner | observed outcome / transient state limitations |
| hidden variants | visibility filtering and hidden candidate rejection |
| unsupported iframe/popup/upload/permission/download | typed capability_gap |

### Run cleanup/isolation rules

Every E2E must:

```text
start from clean backend run state
start with clean fixture route/page state
reset WebSocket/event capture buffers
use unique run_id/test_id
cleanup artifacts or write to unique artifact_bundle_id
not depend on execution order with other tests
```

### Flake policy

| Condition | Policy |
|---|---|
| deterministic assertion failed | fail immediately |
| known async wait issue | one controlled retry allowed only if logged |
| LLM live-output variance | not allowed in CI P0; use mocked/recorded output |
| fixture instability | fix fixture, do not increase retries blindly |
| repeated retry pass | mark flaky and block MVP gate until resolved |

### Artifact retention

Required:

```text
failed runs retained always
passing MVP gate artifacts retained for release evidence
nightly artifacts retained by configured retention window
artifact manifest includes file hashes and redaction report
```

---

## 9. Add TRACE testing strategy to Batch 12

Batch 12 references trace cross-cutting, but must add an explicit trace strategy.

Create/append this as `TEST-TRACE-001 Trace and Observability Test Strategy` or add to Batch 12 patch notes.

### Trace strategy requirements

Trace tests must prove:

```text
trace is evidence, not truth
trace has correlation IDs
trace links events/commands/LLM/DOM/recording/replay/artifacts
trace panel is read-only
trace export has manifest
redaction report exists
fake sensitive data is absent
```

Required trace test groups:

```text
trace identity/correlation tests
lifecycle trace tests
command/rejection trace tests
LLM telemetry trace tests
DOM locator trace tests
recording/codegen trace tests
replay/gap trace tests
frontend trace-panel tests
artifact export tests
redaction corpus tests
```

---

## 10. TEST-MERGE-001 shared contract failure handoff patch

Add this section.

### Shared contract failure ownership

If a shared contract test fails, use this ownership model:

| Failing area | Primary owner | Required collaborator |
|---|---|---|
| backend event envelope | DEV-1 | DEV-3/DEV-4 |
| frontend command envelope | DEV-3 | DEV-1/DEV-4 |
| LLM schema output | DEV-2 | DEV-1 |
| DOM candidate schema | DEV-2 | DEV-4 |
| recording/code_update payload | DEV-1 | DEV-3/DEV-4 |
| trace/artifact export | DEV-4 | DEV-1/DEV-3 |
| MVP flow E2E | DEV-4 | all impacted owners |

### Handoff rule

```text
The developer who finds the failure must attach:
- failing test id
- source rule
- observed payload/event/UI state
- expected contract
- suspected owner
- artifact/log link
```

The owner must respond with:

```text
- root cause classification
- whether source contract or implementation is wrong
- tests to add/update
- narrow fix plan
```

No silent handoff through chat-only context.

---

## 11. Batch 12 patch acceptance criteria

Batch 12 is accepted after:

```text
source-rule/test-property template exists
non-testable source item escape hatch exists
CI tiering and coverage enforcement are defined
backend restart/isolation/late-event coverage is included
LLM/DOM Shadow DOM, tie-break, stale snapshot, context assembly coverage is included
frontend reconnect, Shadow DOM isolation, keyboard/focus, stale race, legacy overlay coverage is included
E2E fixture-to-flow matrix exists
E2E cleanup/flake/artifact retention policy exists
trace/observability test strategy exists
shared contract failure handoff rules exist
```

After this patch:

```text
Batch 12 = testing-doctrine-ready
Batch 13 detailed matrices can be reviewed/used next
```
