# PATCH-011 Batch 13 Detailed Test Matrix Corrections

**Type:** Detailed Test Matrix Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** TEST-HANDOFF-001 and all Batch 13 TEST-MATRIX files  
**Reason:** Codex Batch 13 review found the matrices directionally correct but not complete enough to become the authoritative test-first implementation guide. Required PATCH-010 coverage is missing or partial across backend, event/command, LLM/DOM, frontend, E2E, MVP gate, trace, CI, and source-rule mapping.  
**Decision:** Patch Batch 13. Do not regenerate. Do not use Batch 13 for implementation repo test mapping until this patch is applied.

---

## 1. Codex review result

```text
Confidence: High
Final decision: Patch Batch 13
```

Codex found:

```text
Batch 13 is the row-level test-matrix layer that turns the Batch 12 doctrine into concrete cases.
It is directionally correct, but not yet complete enough to be the authoritative test-first implementation guide.
```

---

## 2. Patch goal

This patch adds:

```text
1. Source-rule / invariant mapping requirement for every matrix row
2. Backend restart, multi-run isolation, corrupted snapshot, late-event, and cross-process tests
3. Legacy/canonical event compatibility and deterministic schema-version behavior
4. LLM/DOM Shadow DOM extraction, candidate tie-break, stale snapshot drift, prompt/context assembly, and confidence-threshold tests
5. Frontend reconnect/disconnect, Shadow DOM isolation, keyboard/focus, stale race, and legacy-overlay migration tests
6. E2E fixture-to-flow mapping, cleanup/isolation, flake policy, artifact-retention tests
7. Dedicated trace/observability test matrix
8. MVP gate additions for trace, source-rule audit, CI tier, artifact manifest hashes, and conditional typed-gap policy
9. Cleanup of vague “or” expected outcomes
```

---

## 3. TEST-HANDOFF-001 row-to-repo mapping template

Add this section.

### Machine-readable test mapping template

Every selected test matrix row must be mapped to repo test files before implementation.

Use this table per implementation slice:

| Field | Required | Example |
|---|---:|---|
| Matrix Test ID | Yes | `BE-N-006` |
| Source Rule ID | Yes | `BE-006` |
| Architecture Invariant | Yes | Backend validates strict cursor |
| Repo Test File | Yes | `tests/test_execution_contract.py` |
| Test Function/Class | Yes | `test_wrong_step_id_rejected` |
| Owner | Yes | `DEV-1` |
| Layer | Yes | unit/contract/integration/e2e |
| Expected Failure Before Fix | Conditional | yes/no |
| Evidence Artifact | Conditional | rejection payload / events.ndjson |
| Status | Yes | missing / existing / added / passing |

### Rule

```text
No implementation starts until every selected P0 matrix row has either:
1. an existing repo test mapped, or
2. a new test file/function planned first.
```

---

## 4. Global matrix row format patch

Every detailed matrix should include or be accompanied by a source-rule mapping table.

Minimum fields:

```text
Test ID
Source Rule ID
Architecture Invariant
Type
Priority
Scenario
Preconditions
Steps/Input
Expected Result
Evidence
Owner
Automation Layer
```

If the current table does not include `Source Rule ID` and `Architecture Invariant`, add a companion mapping table below it.

---

## 5. TEST-MATRIX-BE-001 backend additions

Add these rows.

| Test ID | Source Rule ID | Type | Priority | Scenario | Preconditions | Steps | Expected Result | Evidence |
|---|---|---|---:|---|---|---|---|---|
| BE-ISO-001 | BE-001 | Negative | P0 | Old run event cannot mutate current run | run A completed, run B active | deliver late run A event | run B state unchanged; diagnostic trace | state snapshot + trace |
| BE-ISO-002 | BE-001 | Negative | P0 | Cross-run command_id reuse cannot mutate wrong run | run A command_id reused in run B | send command with stale run_id | typed rejection | rejection payload |
| BE-ISO-003 | BE-006 | Boundary | P0 | Plan IDs cannot cross runs | run A plan, run B active | confirm run A plan on run B | stale/wrong run rejection | rejection payload |
| BE-RESTART-001 | BE-001 | Edge | P0 | Reconnect after backend restart does not fake truth | frontend reconnects after backend restart | request session/read-model | backend returns supported state or typed gap; frontend cache not truth | reconnect/session payload |
| BE-RESTART-002 | BE-001 | Edge | P1 | Backend restart during recovery | recovery open before restart | reconnect/recover | recovery state restored only if backend persisted it; otherwise typed gap | session payload |
| BE-SNAP-001 | REC-008 | Negative | P0 | Corrupted snapshot/load rejected | corrupted snapshot/archive | load snapshot | typed rejection; no runtime mutation | rejection + trace |
| BE-SNAP-002 | REC-008 | Boundary | P1 | Unsupported session restore typed gap | save/load unsupported | request load_session | typed capability/session gap | gap payload |
| BE-LATE-001 | EVENT-001 | Negative | P0 | Late step_recorded after run_completed rejected | run completed | deliver step_recorded | diagnostic/rejection; no recorded mutation | event absence + trace |
| BE-LATE-002 | EVENT-001 | Negative | P0 | Late recovery_needed after run_completed rejected | run completed | deliver recovery_needed | no recovery state opened | state snapshot |
| BE-PROC-001 | REC-008 | Contract | P0 | Archive/schema validated before replay | replay archive exists | validate archive before replay | invalid archive cannot execute | validation result |
| BE-PROC-002 | EVENT-001 | Contract | P0 | Cross-process event has schema_version | event from persisted/process boundary | ingest event | missing/invalid schema rejected | rejection payload |

### Backend expected-result cleanup

Rows with “idempotent or typed rejection” must be resolved during repo inspection into one explicit policy per command.

Required policy table:

| Command/Event | Duplicate behavior |
|---|---|
| confirm | idempotent or typed rejection; choose one |
| correction | typed rejection unless command_id idempotent replay |
| step_recorded | idempotent only if same payload hash; otherwise reject |
| code_update | idempotent only if same source_recording_ids/hash; otherwise reject |
| run_completed | idempotent same terminal payload or duplicate-terminal diagnostic |
| recovery option_selected | idempotent by command_id only; otherwise reject |

---

## 6. TEST-MATRIX-EVENT-001 event/command additions

### Split ambiguous EVENT-C-003

Replace:

```text
Missing schema_version → rejected or normalized by compatibility path
```

with explicit rows:

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| EVENT-C-003A | EVENT-001 | Contract | P0 | Canonical event missing schema_version | rejected |
| EVENT-C-003B | EVENT-001 | Compatibility | P1 | Legacy event missing schema_version through compatibility adapter | normalized with compatibility diagnostic |
| EVENT-C-003C | EVENT-001 | Compatibility | P1 | Legacy event cannot be safely normalized | typed diagnostic; no frontend state mutation |

### Add legacy/canonical compatibility rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| EVENT-COMP-001 | EVENT-001 | Compatibility | P0 | Canonical backend event consumed by frontend | frontend updates from envelope |
| EVENT-COMP-002 | EVENT-001 | Compatibility | P1 | Legacy backend event consumed through adapter | frontend updates with diagnostic trace |
| EVENT-COMP-003 | EVENT-001 | Negative | P0 | Mixed legacy/canonical duplicate payload | no duplicate state mutation |
| EVENT-COMP-004 | EVENT-002 | Negative | P0 | Legacy frontend command missing command_id | typed rejection |
| EVENT-COMP-005 | EVENT-003 | Contract | P0 | Rejection payload includes command_id when command exists | command_id present |
| EVENT-COMP-006 | EVENT-003 | Contract | P0 | Rejection payload includes current_state where available | current_state present or diagnostic says unavailable |
| EVENT-COMP-007 | EVENT-002 | Boundary | P0 | Duplicate command across reconnect | idempotent by command_id or typed duplicate rejection |
| EVENT-COMP-008 | EVENT-001 | Negative | P0 | Out-of-order recovery_needed after run_completed | no recovery state mutation |
| EVENT-COMP-009 | EVENT-001 | Contract | P0 | Event schema version upgrade path | explicit adapter/version handling, not silent mutation |

---

## 7. TEST-MATRIX-LLM-DOM-001 additions

### Shadow DOM-aware extraction rows

| Test ID | Source Rule ID | Type | Priority | Fixture | Scenario | Expected Result |
|---|---|---|---:|---|---|---|
| DOM-SHADOW-001 | DOM-001 | Positive | P0 | Shadow DOM app shell | AutoWorkbench UI mounted in Shadow DOM | app UI controls excluded from target-page candidates |
| DOM-SHADOW-002 | DOM-001 | Negative | P0 | target page with open shadow root | target inside open shadow root | extracted only if policy supports; metadata marks shadow boundary |
| DOM-SHADOW-003 | DOM-001 | Negative | P1 | closed shadow root | target inside closed shadow root | typed limitation/capability gap; no hallucinated target |
| DOM-SHADOW-004 | DOM-004 | Regression | P0 | overlay/control collision | AutoWorkbench confirm button and page confirm button both exist | target-page locator excludes AutoWorkbench control |

### Candidate tie-break determinism rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| DOM-TIE-001 | DOM-003 | Boundary | P0 | Two equivalent visible buttons | deterministic ambiguity or deterministic ranked reason |
| DOM-TIE-002 | DOM-003 | Boundary | P0 | Same text in two sections | section/ancestor context used; if unsafe ask_user |
| DOM-TIE-003 | DOM-003 | Contract | P0 | Candidate metadata complete | candidate_id/visibility/role/name/ancestor/score/confidence present |
| DOM-TIE-004 | DOM-004 | Negative | P0 | Tie-break unsafe but LLM picks one | backend validation blocks/ask_user |

### Stale snapshot / execution drift rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| DOM-DRIFT-001 | DOM-004 | Edge | P0 | DOM changes after plan_ready | backend/browser validation catches stale candidate |
| DOM-DRIFT-002 | DOM-004 | Edge | P0 | element removed before execution | recovery_needed; no blind click |
| DOM-DRIFT-003 | DOM-004 | Edge | P0 | element visible during planning but hidden during execution | hidden validation failure/recovery |
| DOM-DRIFT-004 | DOM-004 | Edge | P0 | SPA route changes after snapshot | wrong-page/stale recovery |
| DOM-DRIFT-005 | DOM-009 | Positive | P0 | update_locator after drift | backend validates new candidate before retry |

### Prompt/context assembly rows

| Test ID | Source Rule ID | Type | Priority | Purpose | Scenario | Expected Result |
|---|---|---|---:|---|---|---|
| LLM-CTX-001 | LLM-002 | Contract | P0 | journey_planner | full raw DOM available | prompt receives summarized/scoped DOM, not full raw DOM |
| LLM-CTX-002 | LLM-002 | Contract | P0 | locator_specialist | conversation history available | specialist receives scoped DOM + intent, not full chat history |
| LLM-CTX-003 | LLM-002 | Contract | P0 | recovery_diagnoser | trace/DOM available | receives failure evidence + relevant candidates only |
| LLM-CTX-004 | LLM-002 | Negative | P0 | any runtime purpose | sensitive data in DOM/history | redacted before prompt |
| LLM-CTX-005 | LLM-002 | Boundary | P0 | huge page | context exceeds budget | compress/ask_more_context/fail safely |
| LLM-CTX-006 | LLM-002 | Contract | P0 | skill loading | conflicting skill/source instructions | PRD/source hierarchy wins; skill precedence trace recorded |

### Confidence threshold rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| LLM-CONF-001 | LLM-008 | Positive | P0 | high confidence + backend valid | may proceed after confirmation |
| LLM-CONF-002 | LLM-008 | Boundary | P0 | medium confidence | ask_user or require stronger validation |
| LLM-CONF-003 | LLM-008 | Negative | P0 | low confidence | ask_user/recovery/more_context; no execution |
| LLM-CONF-004 | LLM-008 | Negative | P0 | unknown confidence | no execution |
| LLM-CONF-005 | DOM-004 | Regression | P0 | LLM high confidence but browser finds 3 matches | ambiguity blocks execution |

---

## 8. TEST-MATRIX-FE-001 additions

### Reconnect/disconnect rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| FE-WS-001 | FE-002 | Edge | P0 | Backend disconnected | visible disconnected state; no fake success |
| FE-WS-002 | FE-003 | Edge | P0 | Pending command during disconnect | pending/error state; no lifecycle mutation |
| FE-WS-003 | FE-002 | Edge | P0 | Reconnect after disconnect | refresh from backend/session state, not local cache truth |
| FE-WS-004 | FE-003 | Edge | P0 | Rejected command after reconnect | rejection visible; user has next safe action |
| FE-WS-005 | FE-002 | Regression | P0 | frontend cache recreates old truth | forbidden |

### Shadow DOM isolation rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| FE-SHADOW-001 | FE-001 | Contract | P0 | Shadow root mounted | aw-root exists inside Shadow DOM |
| FE-SHADOW-002 | FE-001 | Contract | P0 | Style isolation | app styles do not leak to page; page styles do not break panel basics |
| FE-SHADOW-003 | FE-001 | Negative | P0 | Target page locator extraction | AutoWorkbench controls excluded from target-page candidates |
| FE-SHADOW-004 | FE-001 | Boundary | P1 | Unmount/remount | no backend runtime mutation |
| FE-SHADOW-005 | FE-010 | Compatibility | P0 | legacy overlay path still active | compatibility path cannot own runtime truth |

### Keyboard/focus rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| FE-A11Y-003 | FE-009 | Contract | P0 | Confirm via keyboard | command sent once |
| FE-A11Y-004 | FE-009 | Contract | P0 | Focus moves to recovery | recovery_needed focuses/announces recovery region |
| FE-A11Y-005 | FE-009 | Contract | P1 | Panel/modal focus handling | focus trapped only when appropriate |
| FE-A11Y-006 | FE-009 | Edge | P1 | Long panel scroll | critical action buttons remain reachable |
| FE-A11Y-007 | FE-009 | Contract | P0 | Accessible names for core actions | names present |

### Stale confirm/correction race rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| FE-RACE-001 | FE-004 | Boundary | P0 | Confirm while correction pending | confirm disabled or stale rejection shown |
| FE-RACE-002 | FE-004 | Boundary | P0 | Correction response for old plan arrives late | current plan UI unchanged; diagnostic shown |
| FE-RACE-003 | FE-004 | Boundary | P0 | Double correction submit | one command or duplicate rejection |
| FE-RACE-004 | FE-004 | Regression | P0 | Frontend locally replaces plan | forbidden |

### Legacy overlay migration rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| FE-LEGACY-001 | FE-010 | Compatibility | P0 | Legacy overlay active | does not own lifecycle truth |
| FE-LEGACY-002 | FE-010 | Compatibility | P0 | Legacy + Shadow DOM both present | only one command source active or deduped safely |
| FE-LEGACY-003 | FE-010 | Negative | P0 | legacy normalizeBackendMessage creates fake completion | forbidden |
| FE-LEGACY-004 | FE-010 | Audit | P0 | migration audit | active UI path documented |

---

## 9. TEST-MATRIX-E2E-001 additions

### Fixture-to-flow mapping

Add this fixture matrix.

| Fixture class | Required E2E tests |
|---|---|
| clean semantic | E2E-P-001, E2E-P-002, E2E-P-003 |
| weak div/span | E2E-P-007, DOM-N-001, DOM-N-003, FE-PICK-P-001 |
| docs/code-block | E2E-P-004, E2E-P-008 |
| form-heavy | fill/select/required validation flow rows to be added before form implementation |
| cards/table rows | scoped row/card targeting rows before table/card implementation |
| modal/dialog | E2E-E-002, recovery dynamic-state rows |
| portal dropdown | E2E-E-001 |
| toast/loading/spinner | observed-outcome limitation/recovery rows |
| hidden variants | E2E-E-003 |
| unsupported iframe/popup/upload/permission/download | E2E-E-004 + capability_gap rows |

### Cleanup/isolation rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| E2E-ISO-001 | E2E-001 | Contract | P0 | Clean backend state per test | unique run_id/test_id; no previous state |
| E2E-ISO-002 | E2E-004 | Contract | P0 | Clean fixture route/page state | fixture reset before test |
| E2E-ISO-003 | E2E-002 | Contract | P0 | Event capture buffer reset | no prior events |
| E2E-ISO-004 | TRACE-009 | Contract | P0 | Unique artifact bundle | unique artifact_bundle_id |
| E2E-ISO-005 | E2E-001 | Negative | P0 | Test order dependency | tests pass independently/shuffled where practical |

### Flake policy rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| E2E-FLAKE-001 | PLAN-005 | Policy | P0 | Deterministic assertion failed | fail immediately |
| E2E-FLAKE-002 | PLAN-005 | Policy | P1 | Known async wait issue | one controlled retry allowed if logged |
| E2E-FLAKE-003 | LLM-004 | Policy | P0 | Live LLM variance in CI P0 | not allowed; use mocked/recorded output |
| E2E-FLAKE-004 | E2E-004 | Policy | P0 | Fixture instability | fix fixture; do not increase retries blindly |
| E2E-FLAKE-005 | PLAN-005 | Policy | P0 | Repeated retry pass | mark flaky and block MVP gate until resolved |

### Artifact retention / manifest rows

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result |
|---|---|---|---:|---|---|
| E2E-ART-006 | TRACE-009 | Contract | P0 | Manifest includes file hashes | manifest.json file_hashes present |
| E2E-ART-007 | TRACE-009 | Contract | P0 | Failed run retained | artifact bundle retained |
| E2E-ART-008 | TRACE-009 | Contract | P0 | Passing MVP gate retained | release evidence retained |
| E2E-ART-009 | TRACE-010 | Contract | P0 | Redaction report in manifest | report present and linked |
| E2E-ART-010 | TRACE-009 | Boundary | P1 | Missing optional artifact | manifest explains optional absence |
```

---

## 10. Add dedicated trace matrix

Create new file:

```text
.tasks-md/Testing/TEST-MATRIX-TRACE-001 Trace and Observability Test Cases.md
```

Content:

```markdown
# TEST-MATRIX-TRACE-001 Trace and Observability Test Cases

**Type:** Detailed Test Matrix  
**Priority:** P0  
**Owner:** DEV-4 Evidence + DEV-1 Backend + DEV-3 Frontend  
**References:** EPIC-009, TRACE-001 through TRACE-010, PATCH-010

| Test ID | Source Rule ID | Type | Priority | Scenario | Expected Result | Evidence |
|---|---|---|---:|---|---|---|
| TRACE-C-001 | TRACE-001 | Contract | P0 | Trace identity row | trace_id/run_id/source/trace_kind/emitted_at present | trace.ndjson |
| TRACE-C-002 | TRACE-001 | Contract | P0 | Correlation hierarchy | run_id/plan_id/step_id/operation_id linked where available | trace row |
| TRACE-N-001 | TRACE-001 | Negative | P0 | Trace attempts runtime mutation | forbidden; no state mutation | state snapshot |
| TRACE-P-001 | TRACE-002 | Positive | P0 | Lifecycle event trace | run_started/plan_ready/run_completed traced | trace.ndjson |
| TRACE-P-002 | TRACE-003 | Positive | P0 | Command/rejection trace | command_id and rejection_code linked | commands/rejections |
| TRACE-P-003 | TRACE-004 | Positive | P0 | LLM telemetry trace | purpose/model/schema/validation/retry/tokens present | llm telemetry |
| TRACE-P-004 | TRACE-005 | Positive | P0 | DOM locator validation trace | candidate_id/validation_status/route present | locator trace |
| TRACE-P-005 | TRACE-006 | Positive | P0 | Recording/codegen trace | recorded_step_id/source_recording_ids/codegen_version linked | recording trace |
| TRACE-P-006 | TRACE-007 | Positive | P0 | Replay/gap trace | replay_run_id/gap_id linked when applicable | replay-gap trace |
| TRACE-FE-001 | TRACE-008 | Negative | P0 | Trace panel click | display only; no runtime mutation | frontend test |
| TRACE-EXP-001 | TRACE-009 | Contract | P0 | Export manifest | manifest.json with sorted files/hashes | manifest |
| TRACE-EXP-002 | TRACE-009 | Contract | P0 | Summary required | summary.md exists | artifact bundle |
| TRACE-RED-001 | TRACE-010 | Negative | P0 | Fake token redacted | raw fake token absent | redaction report |
| TRACE-RED-002 | TRACE-010 | Negative | P0 | Fake OTP/email/phone redacted | raw values absent/masked | redaction report |
| TRACE-RED-003 | TRACE-010 | Contract | P0 | Redaction report schema | redaction_passed/patterns/files fields present | redaction report |
```

---

## 11. TEST-MATRIX-MVP-001 additions

Add rows:

| Test ID | Type | Priority | Gate Item | Required Evidence | Pass Criteria |
|---|---|---:|---|---|---|
| MVP-GATE-016 | Gate | P0 | Trace/observability gate | TEST-MATRIX-TRACE rows | trace identity/export/redaction tests pass |
| MVP-GATE-017 | Gate | P0 | Source-rule mapping audit | mapping table | every P0 test maps to source rule/invariant |
| MVP-GATE-018 | Gate | P0 | CI tier evidence | CI report | Tier 1 and impacted Tier 2 pass; Tier 3 baseline documented |
| MVP-GATE-019 | Gate | P0 | Artifact manifest hashes | manifest.json | required files sorted and hashed |
| MVP-GATE-020 | Gate | P0 | Typed-gap policy | gap report | typed gaps classified blocking/non-blocking with reason |
| MVP-GATE-021 | Gate | P0 | No vague conditional pass | gate report | no `pass or gap` without explicit policy reason |

### Conditional typed-gap policy

Replay/save-load typed gaps pass only when all are true:

```text
1. Capability is not required for the MVP flow being certified.
2. Gap has typed payload with gap_id/capability/evidence_ref.
3. MVP-GATE-020 classifies it as non-blocking.
4. User-facing behavior is clear and not silent.
5. No backend/LLM/frontend truth invariant is violated.
```

Otherwise typed gap fails the MVP gate.

---

## 12. Batch 13 patch acceptance criteria

Batch 13 is accepted after:

```text
source-rule/invariant mapping requirement added
BE matrix includes restart/isolation/late-event/corrupted snapshot coverage
EVENT matrix has deterministic schema-version and legacy/canonical compatibility rows
LLM/DOM matrix includes Shadow DOM, tie-break, stale drift, context assembly, confidence thresholds
FE matrix includes reconnect/disconnect, Shadow DOM isolation, keyboard/focus, stale race, legacy migration
E2E matrix includes fixture-flow mapping, cleanup/isolation, flake policy, artifact retention
TRACE matrix exists
MVP gate includes trace/source-rule/CI/artifact hash/typed-gap policy gates
vague “or” outcomes are converted into explicit policy rows
```

After this patch:

```text
Batch 13 = test-matrix-ready
Next step = repo test mapping, not implementation
```
