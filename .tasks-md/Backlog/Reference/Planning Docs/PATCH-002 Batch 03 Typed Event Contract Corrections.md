# PATCH-002 Batch 03 Typed Event Contract Corrections

**Type:** Planning Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** EPIC-002 and EVENT-001 through EVENT-010  
**Reason:** Codex Batch 03 review found the typed event contract direction clear, but identified contract ambiguity around `option_selected`, `operation_succeeded`, replay identity, migration audit format, and four-developer coordination.  
**Decision:** Patch Batch 03. Do not regenerate. Do not start implementation from Batch 03 until this patch is applied.  

---

## 1. Codex review result

Codex reviewed EPIC-002 and EVENT-001 through EVENT-010 using only Tasks.md planning files.

Result:

```text
Confidence: Medium
All EVENT stories are ready for repo inspection.
No EVENT story is ready for immediate implementation.
Final decision: Patch Batch 03.
```

Reason:

```text
The core event/command contract is understandable,
but payload semantics and coordination structure need cleanup before freezing.
```

---

## 2. Patch goal

This patch makes EPIC-002 and EVENT stories consistent with the Batch 01 v4 standard.

Patch objectives:

1. Canonicalize `option_selected`.
2. Remove/avoid `operation_succeeded` as a parallel truth event.
3. Clarify replay target identity and modes.
4. Clarify `code_update` emission rules.
5. Strengthen EVENT-010 migration audit format.
6. Add four-developer coordination expectations to every EVENT story.
7. Add explicit dependency graph notes.

---

## 3. Canonical `option_selected` command

Apply this to EVENT-002, EVENT-004, and EVENT-007.

### Canonical command shape

```json
{
  "type": "option_selected",
  "command_id": "cmd_123",
  "schema_version": "1.0",
  "source": "frontend",
  "run_id": "run_123",
  "target": {
    "kind": "clarification",
    "id": "clarification_001"
  },
  "selection": {
    "option_id": "opt_001",
    "value": "Use the selected button"
  },
  "context": {
    "plan_id": "plan_001",
    "plan_version": 2,
    "step_id": "step_001",
    "operation_id": "op_001"
  }
}
```

### Canonical fields

| Field | Required | Meaning |
|---|---|---|
| type | Yes | `option_selected` |
| command_id | Yes | idempotency/correlation |
| source | Yes | frontend/user/system |
| run_id | Yes | active run |
| target.kind | Yes | `clarification` or `recovery` |
| target.id | Yes | clarification_id or recovery_id |
| selection.option_id | Conditional | selected known option |
| selection.value | Conditional | free-form value if option list not used |
| context | Optional | plan/step/operation scope |

### Rules

```text
EVENT-004 may reference option_selected only for plan-review clarification cases.
EVENT-007 owns clarification/recovery option semantics.
EVENT-002 owns the generic command envelope.
There must not be two different option_selected shapes.
```

### Tests to add

```markdown
| EVT-OPT-C-001 | Contract | option_selected for clarification | target.kind=clarification | accepted |
| EVT-OPT-C-002 | Contract | option_selected for recovery | target.kind=recovery | accepted |
| EVT-OPT-C-003 | Contract | option_selected missing target.kind | rejected |
| EVT-OPT-C-004 | Contract | stale option target | old clarification/recovery id | runtime_rejected |
```

---

## 4. Step execution event naming correction

Apply this to EVENT-005.

### Decision

Do **not** introduce `operation_succeeded` as a canonical truth event in P0 unless repo inspection proves there is already an accepted event with that role.

Canonical path:

```text
step_validating
→ step_executing
→ step_failed OR step_recorded later through BE-009
```

Operation-level success can exist internally as backend execution evidence, but it should not compete with `step_recorded`.

### Replacement wording for EVENT-005

Replace:

```text
operation_succeeded if introduced
```

with:

```text
operation_result_internal or execution_evidence_ref may be produced internally, but backend-owned recording truth is exposed through EVENT-006 step_recorded.
```

### Tests to add

```markdown
| EVT005-C-004 | Contract | operation success is not recorded truth | operation success evidence exists | no step_recorded until BE-009 recording builder accepts children |
| EVT005-C-005 | Contract | step_recorded remains canonical recording event | successful execution children | recording event comes from EVENT-006 path |
```

---

## 5. EVENT-006 `code_update` emission clarification

Apply this to EVENT-006.

### Decision

`code_update` must not appear before backend recording is finalized for the relevant step/children.

### Code update rules

| Situation | code_update behavior |
|---|---|
| step_recorded with codegen-ready children | may emit code_update |
| recording incomplete | must not emit code_update |
| diagnostics-only update | allowed only if explicitly marked `diagnostic_only: true` |
| failed recording | emit recording_failed or rejection, not normal code_update |
| child order mismatch | no code_update until resolved |
| expected_outcome only | must not generate assertion code by itself |

### Minimum code_update payload

```json
{
  "type": "code_update",
  "schema_version": "1.0",
  "run_id": "run_123",
  "step_id": "step_001",
  "source_recording_ids": ["recorded_step_001"],
  "lines": ["await page.getByRole('button', { name: 'Submit' }).click();"],
  "diagnostics": [],
  "diagnostic_only": false
}
```

### Tests to add

```markdown
| EVT006-C-004 | Contract | code_update before recording | no recorded_step | rejected |
| EVT006-C-005 | Contract | diagnostic-only update | diagnostic_only=true, no lines | accepted by policy |
| EVT006-C-006 | Contract | expected_outcome only | no executed child evidence | no code_update |
```

---

## 6. EVENT-008 replay identity clarification

Apply this to EVENT-008.

### Replay target modes

| Mode | Required target fields | P0 behavior |
|---|---|---|
| replay_step | recorded_step_id | replay ordered children for one recorded step |
| replay_operation | recorded_step_id + operation_id | replay one child operation/check |
| replay_all | recorded_run_id or session_id | replay recorded steps in order using stop_on_error policy |

### Common replay command envelope

```json
{
  "type": "replay_step",
  "command_id": "cmd_replay_001",
  "schema_version": "1.0",
  "source": "frontend",
  "run_id": "run_123",
  "target": {
    "mode": "replay_step",
    "recorded_step_id": "recorded_step_001",
    "operation_id": null,
    "recorded_run_id": "recorded_run_123"
  },
  "options": {
    "stop_on_error": true
  }
}
```

### Replay result identity

Every replay result must include:

| Field | Required | Meaning |
|---|---|---|
| replay_run_id | Yes | replay attempt identity |
| source_run_id | Conditional | original live run |
| recorded_run_id | Conditional | recorded source |
| recorded_step_id | Conditional | replayed step |
| operation_id | Conditional | replayed operation |
| mode | Yes | replay_step/replay_operation/replay_all |
| precondition_status | Yes | passed/failed/unknown |
| replay_status | Yes | running/passed/failed/stopped |
| evidence_ref | Optional | trace/artifact |

### Tests to add

```markdown
| EVT008-C-004 | Contract | replay_operation without recorded_step_id | operation_id only | rejected |
| EVT008-C-005 | Contract | replay_all without recorded_run_id/session_id | missing source | rejected |
| EVT008-C-006 | Contract | replay_result missing replay_run_id | invalid result | rejected |
```

---

## 7. EVENT-010 migration audit hardening

Apply this to EVENT-010.

### Canonical-vs-legacy mapping output

Repo inspection must produce this table:

| Current name | Current direction | Current payload fields | Canonical target | Decision | Adapter needed | Blocker |
|---|---|---|---|---|---|---|
| example_current_event | backend→frontend | type, step | step_executing | keep/adapt/block | yes/no | missing operation_id |

### Decision values

| Decision | Meaning |
|---|---|
| keep | current name/payload already matches canonical contract |
| adapt | temporary adapter maps current name/payload to canonical |
| block | cannot migrate safely until upstream story fixes missing data |
| deprecate | legacy-only event; do not use for new work |

### Acceptance criteria for EVENT-010

EVENT-010 is accepted only when:

- every current backend event emitter is listed
- every current frontend command handler is listed
- every frontend event consumer is listed
- every legacy overlay/transitional event dependency is marked
- every current name maps to keep/adapt/block/deprecate
- adapter requirements are explicit
- no new work is instructed to target legacy overlay events

### Tests/audit checks

```markdown
| EVT010-A-003 | Audit | every current event mapped | all names listed | no unmapped emitters |
| EVT010-A-004 | Audit | every current command mapped | all commands listed | no unmapped handlers |
| EVT010-A-005 | Audit | adapter preserves canonical required fields | adapted event | canonical payload valid |
| EVT010-A-006 | Audit | legacy overlay-only event | legacy event | deprecate or adapt decision |
```

---

## 8. Four-developer coordination block to add to every EVENT story

Add this standard section to each EVENT story, customizing the first line for that story.

```markdown
## Four-developer coordination

| Developer | Relationship to this story |
|---|---|
| DEV-1 Backend | Primary owner. Defines backend schema/emission/validation path for this event/command contract. |
| DEV-2 LLM | Must not emit runtime truth events directly. Must align LLM schemas with backend-accepted payloads only. |
| DEV-3 Frontend | Consumes typed backend events and sends canonical commands. Must not infer lifecycle truth locally. |
| DEV-4 E2E | Captures payloads and asserts event/command sequence using canonical fields. |

Story-specific coordination:
- DEV-1: <story-specific backend contract>
- DEV-2: <story-specific LLM boundary>
- DEV-3: <story-specific frontend consumer/command behavior>
- DEV-4: <story-specific E2E assertion>
```

### Story-specific notes

#### EVENT-001

```text
DEV-3 and DEV-4 should use the envelope fields, not parse event-specific prose.
```

#### EVENT-002

```text
DEV-3 command UI must send command envelope fields; it must not send direct lifecycle status mutation.
```

#### EVENT-003

```text
DEV-3 must render structured rejection payloads; DEV-4 must assert rejected commands as expected contract outcomes.
```

#### EVENT-004

```text
DEV-3 plan review UI renders plan_ready from backend active plan; DEV-2 plan output remains proposal only.
```

#### EVENT-005

```text
DEV-4 must assert step/operation identity in execution events; DEV-2 proposed tool calls are not execution truth.
```

#### EVENT-006

```text
DEV-3 Recorded/Code tabs consume step_recorded/code_update only; DEV-4 checks no code_update before recording.
```

#### EVENT-007

```text
DEV-3 renders clarification/recovery options from backend payload; DEV-2 may generate question text but not resolve state.
```

#### EVENT-008

```text
DEV-3 replay controls send replay commands only; DEV-4 validates replay precondition failures and result identities.
```

#### EVENT-009

```text
DEV-2 must not hallucinate support for unsupported capability; DEV-4 can assert capability_gap_recorded for unsupported fixtures.
```

#### EVENT-010

```text
All developers must use canonical names for new work; legacy adapter decisions are transitional only.
```

---

## 9. Explicit dependency notes to add

### EVENT-001

```text
Direct blockers: EVENT-003 through EVENT-009.
Indirect consumers: DEV-3 event store, DEV-4 event capture, trace UI.
```

### EVENT-002

```text
Direct blockers: EVENT-003, EVENT-004, EVENT-007, EVENT-008.
Indirect consumers: DEV-3 command UI, DEV-4 command rejection tests.
```

### EVENT-003

```text
Direct blockers: all invalid command/transition paths.
Indirect consumers: frontend error rendering, E2E negative-path assertions.
```

### EVENT-004

```text
Depends on EVENT-001, EVENT-002, EVENT-003, BE-004, BE-005.
Blocks DEV-3 plan review UI and DEV-4 correction/confirmation E2E.
```

### EVENT-005

```text
Depends on EVENT-001, EVENT-003, BE-006.
Blocks execution UI and execution event assertions.
```

### EVENT-006

```text
Depends on EVENT-001, EVENT-003, BE-009.
Blocks recorded/code UI and code_update assertions.
```

### EVENT-007

```text
Depends on EVENT-001, EVENT-002, EVENT-003, BE-008.
Blocks clarification/recovery UI and recovery E2E.
```

### EVENT-008

```text
Depends on EVENT-001, EVENT-002, EVENT-003, BE-012.
Blocks replay controls and replay smoke E2E.
```

### EVENT-009

```text
Depends on EVENT-001, EVENT-003, BE-011.
Blocks capability gap UI/trace and unsupported-flow E2E.
```

### EVENT-010

```text
Depends on EVENT-001 and EVENT-002 plus repo inspection.
Blocks safe migration from legacy/current event names.
```

---

## 10. Batch 03 patch acceptance criteria

Batch 03 is accepted after:

- `option_selected` has one canonical shape.
- EVENT-005 no longer introduces `operation_succeeded` as a parallel recording truth event.
- EVENT-006 clarifies `code_update` cannot occur before finalized recording.
- EVENT-008 includes replay target modes and identity requirements.
- EVENT-010 includes canonical-vs-legacy mapping output.
- Each EVENT story has explicit four-developer coordination.
- Each EVENT story has explicit dependency notes.
- All EVENT stories remain ready for repo inspection, not immediate implementation.

After this patch:

```text
EPIC-002 = planning-ready.
EVENT-001 through EVENT-010 = ready for repo inspection.
EVENT-001 through EVENT-010 = not ready for immediate implementation.
```
