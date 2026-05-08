# PATCH-008 Batch 10 Trace and Observability Corrections

**Type:** Planning Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** EPIC-009 and TRACE-001 through TRACE-010  
**Reason:** Codex Batch 10 review found the trace architecture clear and repo-inspection-ready, but identified dependency and policy-shaping gaps: TRACE-009 should explicitly depend on TRACE-010, trace identity granularity should be clearer, export/redaction linkage should be tightened, and several trace contracts need sharper source/correlation/redaction details.  
**Decision:** Patch Batch 10. Do not regenerate. Do not start implementation from Batch 10 until this patch is applied.

---

## 1. Codex review result

Codex reviewed EPIC-009 and TRACE-001 through TRACE-010 using only Tasks.md planning files.

Result:

```text
Confidence: Medium
All TRACE-001 through TRACE-010 are ready for repo inspection.
No TRACE story is ready for immediate implementation.
Final decision: Patch Batch 10.
```

Reason:

```text
The trace epic is structurally sound and strong enough to prevent trace from becoming runtime truth,
but the batch needs small dependency/policy refinements before freezing.
```

---

## 2. Patch goal

Patch objectives:

1. Add explicit TRACE-009 dependency on TRACE-010.
2. Clarify trace identity granularity and correlation hierarchy.
3. Clarify backend lifecycle trace edge behavior.
4. Clarify command/rejection source classification and redacted payload shape.
5. Tighten LLM telemetry validation-status and backend-validator semantics.
6. Clarify DOM/locator trace route values and redacted DOM summary shape.
7. Make TRACE-006 coupling to EPIC-008 explicit.
8. Clarify replay/capability-gap trace relationship.
9. Clarify frontend trace panel filter/export/row expansion behavior.
10. Tighten artifact export manifest, deterministic ordering, and summary rules.
11. Add explicit redaction test corpus / forbidden-pattern examples.
12. Make four-developer coordination more story-specific for TRACE-004, TRACE-008, TRACE-009, and TRACE-010.

---

## 3. EPIC-009 invariant reinforcement

Apply this to EPIC-009.

### Non-negotiable invariant

```text
Trace is evidence, not truth.
Trace may explain, correlate, export, summarize, and display runtime evidence.
Trace must never create, mutate, repair, complete, reject, accept, or override runtime state.
```

### Trace consumer rule

| Consumer | Allowed | Forbidden |
|---|---|---|
| Backend | write trace records from existing truth/evidence | derive lifecycle truth from trace |
| LLM | read trace for explanation/debug suggestions | decide runtime finality |
| Frontend | display trace as diagnostics | infer lifecycle state from trace rows |
| E2E | assert trace/artifact presence | treat trace as substitute for backend event truth |

---

## 4. TRACE-001 identity granularity patch

Apply this to TRACE-001.

### Trace identity levels

| ID | Granularity | Required meaning |
|---|---|---|
| trace_id | single trace record row | unique per trace record |
| trace_session_id | optional run-level trace collection | groups all trace rows for one run/session |
| artifact_bundle_id | exported artifact bundle | groups exported files |
| evidence_ref | pointer to evidence artifact | can point to screenshot, payload, log excerpt, DOM snapshot, etc. |

### Correlation hierarchy

Use this hierarchy where available:

```text
artifact_bundle_id
  → trace_session_id
    → run_id
      → plan_id / plan_version
        → step_id
          → operation_id
            → recorded_step_id / recorded_child_id
              → codegen_version / code_update_ref
```

Replay can branch from the original run:

```text
run_id
  → replay_run_id
    → recorded_run_id / recorded_step_id / operation_id
```

LLM trace links by:

```text
run_id
  → llm_call_id
    → purpose / schema_id / validation_status
```

### Field relationship rules

| Field | Rule |
|---|---|
| trace_kind | domain of evidence: lifecycle/command/llm/dom/recording/replay/frontend/export/redaction |
| source | subsystem that emitted the trace record |
| evidence_ref | artifact pointer, not runtime truth |
| trace_id | unique record ID, not run ID |
| run_id | primary runtime correlation when run-scoped |

### Tests to add

```markdown
| TRACE001-C-004 | Contract | trace_id uniqueness | duplicate trace_id | rejected |
| TRACE001-C-005 | Contract | trace_session groups run rows | same trace_session_id | accepted |
| TRACE001-C-006 | Contract | replay branch correlation | replay_run_id + recorded_step_id | accepted |
```

---

## 5. TRACE-002 lifecycle edge behavior patch

Apply this to TRACE-002.

### Lifecycle edge behavior

| Situation | Required trace behavior |
|---|---|
| duplicate terminal event | trace both rows, flag duplicate_terminal=true, do not mutate state |
| reconnect/session_state | trace reconnect/session_state as evidence; do not reconstruct truth locally |
| stale plan event | trace stale plan_version and backend rejection if emitted |
| missing payload hash | allowed only with diagnostic warning |
| event emitted during shutdown | trace if observed; do not mark success |
| unknown event type | trace as unknown_event if policy allows, otherwise reject with diagnostic |

### Payload hash policy

```text
payload_hash is recommended for lifecycle event trace records.
If omitted, diagnostic_summary must explain why.
Payload hash is evidence integrity support, not truth authority.
```

### Tests to add

```markdown
| TRACE002-U-004 | Unit | duplicate run_completed | duplicate_terminal flagged |
| TRACE002-U-005 | Unit | reconnect session_state | traced as evidence only |
| TRACE002-U-006 | Unit | missing payload_hash | diagnostic warning |
```

---

## 6. TRACE-003 command source and redaction patch

Apply this to TRACE-003.

### Command source classification

| source value | Meaning |
|---|---|
| user | direct user action/request |
| frontend | UI-dispatched command envelope |
| backend | backend-generated internal command/effect where allowed |
| system | harness/replay/system command |
| test | E2E/test harness command |

### Redacted payload shape

`payload_redacted` should be a normalized safe summary, not raw payload.

Minimum shape:

```json
{
  "redaction_applied": true,
  "fields_present": ["run_id", "plan_id", "plan_version"],
  "sensitive_fields_removed": ["input_value"],
  "payload_hash": "sha256:...",
  "summary": "confirmed command for plan_version 2"
}
```

### Tests to add

```markdown
| TRACE003-U-004 | Unit | frontend command source | source=frontend |
| TRACE003-U-005 | Unit | test harness command | source=test |
| TRACE003-U-006 | Unit | raw sensitive payload | redacted summary + hash |
```

---

## 7. TRACE-004 LLM validation-status patch

Apply this to TRACE-004.

### Validation status values

| validation_status | Meaning |
|---|---|
| not_applicable | purpose has no structured output |
| parse_failed | parser could not extract structured payload |
| schema_invalid | output failed schema |
| retrying | retry requested |
| schema_valid | schema passed |
| backend_rejected | backend validator rejected schema-valid output |
| accepted | backend accepted output/proposal |
| retry_failed | retry exhausted |
| telemetry_failed | telemetry collection failed |

### Backend validator relationship

| Case | Required trace behavior |
|---|---|
| schema invalid | do not call backend validator |
| schema valid + runtime-impacting | call backend validator and trace result |
| backend rejects | validation_status=backend_rejected, no schema retry |
| backend accepts | validation_status=accepted |
| non-runtime-impacting summary | backend_validator may be null |

### Streamed output rule

```text
For streamed model output, trace a final aggregate record after stream completion.
Partial chunks may be debug-only and must not be used as accepted output.
```

### Tests to add

```markdown
| TRACE004-U-005 | Unit | schema valid but backend rejects | backend_rejected |
| TRACE004-U-006 | Unit | streamed output | final aggregate trace |
| TRACE004-U-007 | Unit | parse failure | parse_failed then retrying |
```

---

## 8. TRACE-005 DOM route and redacted summary patch

Apply this to TRACE-005.

### Canonical route values

| route | Meaning |
|---|---|
| allow_execution | unique/actionable locator validated |
| ask_user | ambiguity with user-meaningful options |
| ask_specialist | technical ambiguity or weak evidence |
| request_more_context | insufficient DOM/snapshot evidence |
| recovery | failed/stale/hidden/disabled/wrong-page path |
| update_locator | accepted or requested locator update path |
| capability_gap | unsupported iframe/popup/upload/permission/closed shadow |
| block | unsafe/invalid target with no safe next action |

### Redacted DOM summary shape

```json
{
  "redaction_applied": true,
  "page_title": "Docs Fixture",
  "url_origin": "local-fixture",
  "candidate_count": 4,
  "visible_candidate_count": 2,
  "roles_seen": ["button", "link", "textbox"],
  "text_samples_hashes": ["sha256:..."],
  "sensitive_text_removed": true
}
```

### Tests to add

```markdown
| TRACE005-U-004 | Unit | route ask_user | canonical route |
| TRACE005-U-005 | Unit | route capability_gap | unsupported target |
| TRACE005-U-006 | Unit | redacted DOM summary | no raw sensitive text |
```

---

## 9. TRACE-006 EPIC-008 coupling patch

Apply this to TRACE-006.

### Dependency header correction

Add explicit dependencies:

```text
EPIC-008 Recording and Codegen
REC-001 Recorded step parent-child data model
REC-004 Deterministic Playwright codegen from recorded children
REC-005 code_update event payload and UI integration
REC-009 Codegen reviewer and diagnostics baseline
```

### Required source row

Add:

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| EPIC-008 | Recording/codegen is backend-owned and evidence-backed. | Trace must observe recording/codegen without modifying it. | TRACE-006 links recorded_step_id, recorded_child_id, source_recording_ids, and codegen_version. |

### Tests to add

```markdown
| TRACE006-U-004 | Unit | trace has EPIC-008 IDs | recorded_step_id + codegen_version |
| TRACE006-U-005 | Unit | trace attempts to alter code_update | forbidden |
```

---

## 10. TRACE-007 replay + capability gap relationship patch

Apply this to TRACE-007.

### Combined replay/gap case

When replay fails because an unsupported capability is encountered:

```text
replay_result remains the replay truth event/evidence
capability_gap_recorded remains the gap truth event/evidence
TRACE-007 links both using run_id/replay_run_id/gap_id/evidence_ref
Trace must not collapse them into one status.
```

### Relationship fields

| Field | Required when |
|---|---|
| replay_run_id | replay evidence exists |
| replay_status | replay_result exists |
| gap_id | capability gap exists |
| needed_capability | gap exists |
| linked_gap_id | replay failure caused by gap |
| linked_replay_run_id | gap discovered during replay |
| evidence_ref | available evidence |

### Tests to add

```markdown
| TRACE007-U-004 | Unit | replay failure due to gap | replay and gap linked but separate |
| TRACE007-U-005 | Unit | gap outside replay | no replay_run_id required |
| TRACE007-U-006 | Unit | replay trace marks capability supported | forbidden |
```

---

## 11. TRACE-008 filter/export/row expansion patch

Apply this to TRACE-008.

### Filter behavior

Allowed filters:

```text
run_id
trace_kind
source
event_type
command_id
step_id
operation_id
recorded_step_id
replay_run_id
severity
time range
redaction_applied
```

Filters must not alter runtime or trace source records. They only affect UI display.

### Row expansion behavior

| Row expansion | Rule |
|---|---|
| default | show summary + IDs |
| expanded | show redacted payload/evidence metadata |
| raw payload | hidden unless debug policy allows and redaction passes |
| missing evidence_ref | show warning |
| export from filtered view | export must include filter metadata |

### Tests to add

```markdown
| TRACE008-U-004 | Unit | apply filter | display-only change |
| TRACE008-U-005 | Unit | expand row | redacted payload only |
| TRACE008-U-006 | Unit | export filtered view | filter metadata included |
```

---

## 12. TRACE-009 export manifest and deterministic ordering patch

Apply this to TRACE-009.

### Dependency header correction

Add explicit dependency:

```text
TRACE-010 Observability regression and redaction policy
```

Reason:

```text
TRACE-009 export format requires redaction-report.json and must follow TRACE-010 redaction rules.
```

### Required manifest

Every export must include:

```text
manifest.json
```

Minimum manifest fields:

| Field | Required |
|---|---|
| artifact_bundle_id | Yes |
| run_id | Conditional |
| test_id | Conditional |
| created_at | Yes |
| files | Yes |
| file_hashes | Yes |
| redaction_report | Yes |
| export_version | Yes |
| summary_file | Yes |
| missing_optional_files | Optional |
| failed_required_files | Optional |

### Deterministic file ordering

```text
manifest.files must be sorted lexicographically by relative path.
summary.md should list key evidence in deterministic section order.
NDJSON rows should preserve original emitted order and include emitted_at.
```

### Required vs conditional summary

```text
summary.md is always required.
manifest.json is always required.
redaction-report.json is always required.
Optional files may be absent only if manifest.missing_optional_files explains why.
```

### Tests to add

```markdown
| TRACE009-U-004 | Unit | manifest present | required fields |
| TRACE009-U-005 | Unit | deterministic file order | sorted manifest |
| TRACE009-U-006 | Unit | missing summary | export fails |
| TRACE009-U-007 | Unit | missing redaction report | export fails |
```

---

## 13. TRACE-010 redaction test corpus patch

Apply this to TRACE-010.

### Redaction test corpus

Create or define a local test corpus during implementation containing safe fake examples of:

| Pattern | Example type |
|---|---|
| API key/token | fake token string |
| OTP/auth code | fake 6-digit code |
| email address | fake user@example.test |
| phone number | fake phone number |
| resume/private upload text | fake resume paragraph |
| password field | fake password |
| long user input | long paragraph |
| URL with sensitive query params | local fake URL |
| raw LLM prompt with sensitive field | fake prompt |
| DOM text containing sensitive content | local fixture text |

### Forbidden export patterns

By default, exported trace/artifact files must not contain raw:

```text
API keys
tokens
passwords
OTP/auth codes
private email/phone values
raw resume/private upload contents
unredacted long user-provided text
sensitive query params
```

### Redaction report minimum

```json
{
  "redaction_passed": true,
  "patterns_checked": ["token", "otp", "email", "phone", "password"],
  "findings": [],
  "files_checked": ["trace.ndjson", "commands.json"],
  "redaction_version": "1.0"
}
```

### Tests to add

```markdown
| TRACE010-U-004 | Unit | fake OTP in trace | redacted |
| TRACE010-U-005 | Unit | fake email in command payload | redacted/masked |
| TRACE010-U-006 | Unit | sensitive query param | redacted |
| TRACE010-U-007 | Unit | redaction report schema | valid |
```

---

## 14. Four-developer coordination tightening

Apply these story-specific coordination details.

### TRACE-004

```text
DEV-2 owns LLM telemetry field semantics.
DEV-1 owns backend validator outcome.
DEV-4 asserts schema retry/fail-closed traces.
DEV-3 displays LLM trace as diagnostic only.
```

### TRACE-008

```text
DEV-3 owns the read-only diagnostic panel, filters, expansion, and export UI.
DEV-1/DEV-2 provide trace payloads only.
DEV-4 asserts panel interactions do not mutate runtime or trace source data.
```

### TRACE-009

```text
DEV-4 owns artifact export format and manifest checks.
DEV-1/DEV-2/DEV-3 contribute domain-specific evidence files.
DEV-4 must verify redaction-report.json is present before export is accepted.
```

### TRACE-010

```text
DEV-4 owns redaction regression suite.
DEV-1 marks backend sensitive fields.
DEV-2 ensures LLM prompts/outputs are redacted.
DEV-3 prevents UI from exposing unredacted trace payloads.
```

---

## 15. Batch 10 patch acceptance criteria

Batch 10 is accepted after:

- EPIC-009 invariant is reinforced: trace is evidence, not truth.
- TRACE-001 defines trace_id / trace_session_id / artifact_bundle_id / evidence_ref granularity.
- TRACE-001 defines correlation hierarchy and trace_kind/source relationship.
- TRACE-002 defines duplicate terminal/reconnect/stale/missing-hash behavior.
- TRACE-003 defines command source values and redacted payload shape.
- TRACE-004 defines validation_status values and backend-validator relationship.
- TRACE-005 defines canonical route values and redacted DOM summary shape.
- TRACE-006 explicitly depends on EPIC-008/REC stories and forbids trace mutation of code_update.
- TRACE-007 defines replay/gap linked-but-separate evidence.
- TRACE-008 defines filter/export/row expansion behavior.
- TRACE-009 explicitly depends on TRACE-010, requires manifest.json, deterministic ordering, summary.md, and redaction-report.json.
- TRACE-010 defines redaction corpus, forbidden export patterns, and redaction report shape.
- Four-developer coordination is tightened for TRACE-004, TRACE-008, TRACE-009, and TRACE-010.

After this patch:

```text
EPIC-009 = planning-ready.
TRACE-001 through TRACE-010 = ready for repo inspection.
TRACE-001 through TRACE-010 = not ready for immediate implementation.
```
