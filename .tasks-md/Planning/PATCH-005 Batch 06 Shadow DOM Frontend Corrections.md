# PATCH-005 Batch 06 Shadow DOM Frontend Corrections

**Type:** Planning Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** EPIC-005 and FE-001 through FE-010  
**Reason:** Codex Batch 06 review found the frontend architecture direction clear enough for repo inspection, but identified missing PLAN-002 sections in FE-004 through FE-010, incomplete source evidence tables, missing four-developer coordination blocks, and contract gaps around mount lifecycle, event store behavior, command idempotency, plan/recovery UI, recorded/code/trace boundaries, picker UI, test hooks, and legacy overlay migration.  
**Decision:** Patch Batch 06. Do not regenerate. Do not start implementation from Batch 06 until this patch is applied.

---

## 1. Codex review result

Codex reviewed EPIC-005 and FE-001 through FE-010 using only Tasks.md planning files.

Result:

```text
Confidence: Medium
All FE-001 through FE-010 are ready for repo inspection.
No FE story is ready for immediate implementation.
Final decision: Patch Batch 06.
```

Reason:

```text
The architecture is clear and strong enough to prevent frontend-owned runtime truth,
but the batch is missing required story-template details and needs stronger frontend contract precision before freezing.
```

---

## 2. Patch goal

Patch objectives:

1. Add source evidence tables to every FE story.
2. Add four-developer coordination blocks to every FE story.
3. Add missing PLAN-002 sections to FE-004 through FE-010.
4. Tighten Shadow DOM mount lifecycle behavior.
5. Tighten typed event store behavior for out-of-order/stale/duplicate events.
6. Tighten command dispatcher idempotency and correlation behavior.
7. Clarify plan review, correction, clarification, and recovery UI rules.
8. Clarify recorded/code and trace panel boundaries.
9. Clarify picker/candidate display and update_locator behavior.
10. Clarify frontend test hook/accessibility naming.
11. Clarify legacy overlay migration audit output and done criteria.

---

## 3. Source evidence table requirement for all FE stories

Apply this to FE-001 through FE-010.

Every FE story must include a source evidence table using this format:

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| SOURCE-001 | Frontend renders backend state and collects user input; it must not infer lifecycle from LLM prose. | Frontend is a typed read-model and command sender only. | Story must not create frontend-owned runtime truth. |
| Frontend/UI Spec | Shadow DOM host is primary frontend target; current injected overlay is legacy/transitional. | New product UI targets Shadow DOM. | Story must not grow legacy overlay architecture. |
| EPIC-002 / EVENT contracts | Backend events and frontend commands are typed. | Frontend consumes canonical events and emits canonical commands. | Story must define event/command dependencies. |
| EPIC-001 / BE stories | Backend owns lifecycle, execution, recording, completion truth. | UI renders truth but cannot decide it. | Story must reject local lifecycle mutation. |
| PLAN-005 | E2E needs stable hooks and evidence. | UI needs stable selectors/accessibility. | Story must include testability rules. |

Story-specific evidence rows:

- FE-004: `plan_ready` comes from backend active plan; confirmation must include run_id, plan_id, plan_version.
- FE-005: clarification/recovery options come from backend events; UI cannot resolve recovery truth.
- FE-006: `step_recorded` and `code_update` are backend-owned; expected_outcome is metadata only.
- FE-007: trace/telemetry/evidence are diagnostic read-models, not runtime truth.
- FE-008: picker displays candidates/ancestors; backend validates final locator truth.
- FE-009: stable hooks and accessible roles are required for E2E.
- FE-010: legacy overlay is transitional; new work targets Shadow DOM.

---

## 4. Four-developer coordination block to add to every FE story

Add this standard section to each FE story.

```markdown
## Four-developer coordination

| Developer | Relationship to this story |
|---|---|
| DEV-1 Backend | Provides typed backend events, validates commands, and owns runtime truth. |
| DEV-2 LLM/DOM | Provides LLM proposals or DOM candidates only; does not own frontend/runtime truth. |
| DEV-3 Frontend | Primary owner. Renders backend truth and sends canonical commands. |
| DEV-4 E2E | Tests UI state, command flow, accessibility hooks, and event-backed rendering. |

Story-specific coordination:
- DEV-1: <backend event/command responsibility>
- DEV-2: <LLM/DOM proposal/candidate boundary>
- DEV-3: <frontend implementation boundary>
- DEV-4: <E2E/assertion responsibility>
```

### Story-specific notes

#### FE-001

```text
DEV-1 provides ready/session events if needed; DEV-4 validates host mount/unmount across fixture pages.
```

#### FE-002

```text
DEV-1 owns canonical event payloads; DEV-3 mirrors them in a read-only store; DEV-4 asserts no local lifecycle inference.
```

#### FE-003

```text
DEV-1 validates commands; DEV-3 dispatches canonical envelopes only; DEV-4 tests rejection/idempotency cases.
```

#### FE-004

```text
DEV-1 owns active plan and confirmation validation; DEV-3 renders plan_ready and sends confirm/correction commands; DEV-4 tests stale plan rejection.
```

#### FE-005

```text
DEV-1 owns clarification/recovery state; DEV-2 may generate question text/options; DEV-3 renders options; DEV-4 tests user decision flows.
```

#### FE-006

```text
DEV-1 owns step_recorded/code_update; DEV-3 renders parent/child/code order exactly; DEV-4 tests no code panel update before recording.
```

#### FE-007

```text
DEV-1/DEV-2 provide events/telemetry/evidence refs; DEV-3 displays diagnostics only; DEV-4 validates trace explains failure without inventing state.
```

#### FE-008

```text
DEV-2/DOM provides candidates; DEV-3 displays candidate levels; DEV-1 validates update_locator/final locator; DEV-4 tests picker target levels.
```

#### FE-009

```text
DEV-3 owns test hooks/accessibility; DEV-4 consumes them; hooks must not interfere with target-page automation.
```

#### FE-010

```text
All developers must use canonical Shadow DOM/event contracts for new work; legacy overlay mapping is transitional.
```

---

## 5. FE-001 mount lifecycle patch

Apply this to FE-001.

### Mount lifecycle requirements

| Situation | Required behavior |
|---|---|
| initial injection | create exactly one Shadow DOM host |
| duplicate injection | detect existing host and no-op or update safely |
| page navigation / SPA route change | preserve or remount intentionally without duplicate roots |
| hard reload | clean reinitialization |
| unmount | remove listeners, timers, DOM root, and subscriptions |
| host error | render isolated error boundary state |
| backend disconnected | show disconnected state without mutating runtime truth |
| target page CSS conflict | Shadow DOM isolation prevents style leak |
| product page target extraction | AutoWorkbench UI excluded from target-page DOM extraction unless explicitly inspecting product UI |

### Tests to add

```markdown
| FE001-U-004 | Unit | duplicate injection | no duplicate host |
| FE001-U-005 | Unit | unmount cleanup | listeners/subscriptions removed |
| FE001-U-006 | Unit | error boundary | safe error state |
| FE001-I-002 | Integration | SPA route change | host remains stable or remounts once |
| FE001-I-003 | Integration | backend disconnect | disconnected UI state only |
```

---

## 6. FE-002 typed event store patch

Apply this to FE-002.

### Event store behavior

| Event situation | Required behavior |
|---|---|
| valid event | update matching read-model slice |
| unknown event type | log/reject; do not mutate lifecycle state |
| malformed payload | reject and show diagnostic if needed |
| stale plan_version | ignore/reject and show stale warning |
| duplicate terminal event | idempotent no-op or warning; no repeated mutation |
| out-of-order event | reject, buffer, or request session_state by policy |
| reconnect | request/load backend session_state; do not reconstruct from UI |
| event for unknown run_id | ignore/reject unless session load path accepts it |
| LLM prose message | display as text only; no state mutation |

### Store slice ownership

| Store slice | Backend source | Frontend allowed behavior |
|---|---|---|
| run | run_started/run_completed/session_state | mirror only |
| plan | plan_ready | mirror only |
| execution | step_validating/step_executing/step_failed | mirror only |
| recovery | clarification_needed/recovery_needed | mirror only |
| recording/code | step_recorded/code_update | mirror only |
| trace | evidence/telemetry/rejections | display only |

### Tests to add

```markdown
| FE002-U-005 | Unit | out-of-order event | rejected/buffered by policy |
| FE002-U-006 | Unit | reconnect | requests/uses session_state |
| FE002-U-007 | Unit | duplicate run_completed | idempotent |
| FE002-U-008 | Unit | stale plan_ready | ignored or stale warning |
```

---

## 7. FE-003 command dispatcher patch

Apply this to FE-003.

### Command idempotency and correlation

Every command must include:

| Field | Required | Meaning |
|---|---|---|
| type | Yes | canonical command name |
| command_id | Yes | unique idempotency/correlation id |
| schema_version | Yes | command contract version |
| source | Yes | frontend/user/system |
| run_id | Conditional | run scope |
| plan_id/plan_version | Conditional | plan commands |
| step_id/operation_id | Conditional | step/op commands |
| payload | Yes | command body |

### Dispatcher behavior

| Situation | Required behavior |
|---|---|
| duplicate user click | same command disabled or deduplicated until result |
| backend rejects command | render runtime_rejected; do not mutate truth |
| websocket disconnected | queue only safe commands or block with UI message |
| stale plan in UI | backend rejection shown; store does not self-correct except from backend event |
| command timeout | show pending/failed diagnostic; no local truth mutation |
| command success | wait for backend event/state update |

### Tests to add

```markdown
| FE003-U-005 | Unit | duplicate confirm click | one command or deduped command_id |
| FE003-U-006 | Unit | disconnected command | blocked or queued by policy |
| FE003-U-007 | Unit | command timeout | diagnostic shown |
| FE003-U-008 | Unit | backend rejection | no optimistic truth mutation |
```

---

## 8. FE-004 plan review UI patch

Apply this to FE-004.

### Plan review rendering rules

| UI behavior | Required rule |
|---|---|
| render plan | from `plan_ready` only |
| confirm | command includes run_id, plan_id, plan_version |
| correction | command includes current plan identity and user correction text/diff |
| correction pending | UI may show pending state but cannot mutate plan locally |
| revised plan | renders only after backend emits new plan_ready |
| stale rejection | show runtime_rejected and keep backend-current store |
| execution state | shown only after backend event confirms executing |
| LLM explanation | displayed as non-truth helper text only |

### Plan review UI fields

| Field | Required |
|---|---|
| plan_id/version display or internal ref | Yes |
| ordered steps | Yes |
| child operations summary | Yes |
| expected_outcome metadata | Optional display only |
| confirm action | Yes |
| correction input/action | Yes |
| rejection/error area | Yes |

### Tests to add

```markdown
| FE004-U-005 | Unit | revised plan only after backend event | local correction does not replace plan |
| FE004-U-006 | Unit | confirm missing plan_version | command invalid/not sent |
| FE004-U-007 | Unit | LLM explanation shown | no store mutation |
| FE004-I-002 | Integration | stale confirm rejected | rejection shown, no executing UI |
```

---

## 9. FE-005 clarification and recovery UI patch

Apply this to FE-005.

### Clarification/recovery boundary

| UI action | Required behavior |
|---|---|
| answer clarification | send option_selected with target.kind=clarification |
| choose recovery option | send option_selected with target.kind=recovery |
| skip step | require reason and send skip_step |
| stop run | send stop_run |
| update locator | send update_locator command |
| retry | send backend-approved recovery option command |
| resolve recovery | cannot be done locally |

### Backend rejection behavior

If backend rejects option/skip/retry:

```text
show structured rejection
keep recovery/clarification open unless backend event changes it
do not mark resolved locally
```

### Tests to add

```markdown
| FE005-U-005 | Unit | clarification option_selected | target.kind=clarification |
| FE005-U-006 | Unit | recovery option_selected | target.kind=recovery |
| FE005-U-007 | Unit | backend rejects recovery option | recovery remains open |
| FE005-U-008 | Unit | skip reason required | cannot send empty reason |
```

---

## 10. FE-006 recorded/code panel patch

Apply this to FE-006.

### Panel boundary

| Panel | Source | Rule |
|---|---|---|
| Recorded steps | step_recorded | backend-owned parent/child payload |
| Child operations | step_recorded.children | preserve backend order |
| Code | code_update.lines | no local code generation |
| Diagnostics | code_update.diagnostics | display only |
| Metadata | expected_outcome_metadata | display only; not assertion/code input |

### Ordering and update rules

| Situation | Required behavior |
|---|---|
| step_recorded arrives | append/update recorded row by recorded_step_id |
| duplicate step_recorded | idempotent update or warning |
| code_update before step_recorded | show diagnostic or ignore by policy |
| child order mismatch | render backend order and show warning if event says mismatch |
| long code output | virtualize/collapse safely |
| diagnostic_only update | show diagnostics without code replacement |

### Tests to add

```markdown
| FE006-U-005 | Unit | code_update before recording | no false recorded state |
| FE006-U-006 | Unit | duplicate step_recorded | idempotent |
| FE006-U-007 | Unit | expected_outcome metadata | displayed separately |
| FE006-U-008 | Unit | long code output | still accessible/testable |
```

---

## 11. FE-007 trace panel patch

Apply this to FE-007.

### Trace panel boundary

Trace panel displays evidence. It does not create runtime truth.

### Trace grouping

| Group | Examples |
|---|---|
| runtime lifecycle | run_started, plan_ready, run_completed |
| command/rejection | command sent, runtime_rejected |
| LLM telemetry | purpose, model, tokens, validation status |
| DOM/locator | candidate, validation result, ambiguity |
| recovery | failure, options, selected option |
| recording/code | step_recorded, code_update |
| replay/gap | replay_result, capability_gap_recorded |

### Redaction and summarization

| Situation | Required behavior |
|---|---|
| long payload | summarize with expandable raw/evidence_ref |
| sensitive input | redact by policy where available |
| missing evidence_ref | show “no evidence ref” warning |
| telemetry failure | show warning, do not alter runtime state |
| copied trace | preserve structured fields |

### Tests to add

```markdown
| FE007-U-004 | Unit | long payload | summarized + expandable |
| FE007-U-005 | Unit | sensitive field marker | redacted if policy marks |
| FE007-U-006 | Unit | missing evidence_ref | warning shown |
| FE007-U-007 | Unit | telemetry event | grouped under LLM telemetry |
```

---

## 12. FE-008 picker/candidate UI patch

Apply this to FE-008.

### Candidate display rules

| Candidate type | UI behavior |
|---|---|
| exact node | display as lowest-level option |
| interactive ancestor | highlight as likely click/action target |
| form control/group | show label/control relationship |
| card/row/list item | show scoped container |
| dialog/modal | show modal scope |
| section/container | show section-level scope |
| code/text block | show assertion-friendly text target |
| hidden/disabled/stale | show warning and block direct accept unless backend policy allows |

### Locator truth boundary

```text
Selecting a candidate in UI sends command/selection.
It does not make the locator final.
Backend/browser validation decides whether it can be used.
```

### update_locator surface

| Action | Command |
|---|---|
| choose candidate for failed op | update_locator |
| provide user hint | update_locator with user_hint |
| cancel update | recovery option/stop/no-op |
| candidate rejected | show backend rejection |

### Tests to add

```markdown
| FE008-U-005 | Unit | exact node and ancestor | both displayed with levels |
| FE008-U-006 | Unit | candidate selected | sends update_locator, no local truth |
| FE008-U-007 | Unit | hidden candidate | warning + blocked accept |
| FE008-U-008 | Unit | backend rejects candidate | rejection shown |
```

---

## 13. FE-009 test hooks and accessibility patch

Apply this to FE-009.

### Hook naming pattern

Use stable hooks under the Shadow DOM root.

Suggested pattern:

```text
aw-root
aw-panel-plan
aw-panel-recovery
aw-panel-recorded
aw-panel-code
aw-panel-trace
aw-picker
aw-picker-candidate-row
aw-command-confirm
aw-command-correct
aw-command-stop
aw-command-skip
aw-command-replay
aw-status-run
aw-status-plan
aw-status-execution
```

Exact names can be adjusted after repo inspection, but they must be stable and documented.

### Accessibility expectations

| UI element | Required |
|---|---|
| main panel | role/label or labelled region |
| prompt input | labelled textbox |
| confirm/correct/stop/skip buttons | role button + accessible name |
| dialogs/recovery cards | labelled region/dialog |
| candidate rows | readable labels and selected state |
| code panel | accessible code/text region |
| trace panel | readable list/log region |

### Non-interference rule

```text
Frontend test hooks must not be used as target-page automation locators.
AutoWorkbench UI hooks are scoped inside the Shadow DOM host.
Target-page DOM extraction should exclude AutoWorkbench UI unless product UI itself is under test.
```

### Tests to add

```markdown
| FE009-U-004 | Unit | hook naming pattern | required hooks present |
| FE009-U-005 | Unit | accessible command buttons | role/name present |
| FE009-U-006 | Unit | hooks scoped to shadow root | no target-page pollution |
| FE009-E-003 | E2E | interact via hooks | stable across fixture pages |
```

---

## 14. FE-010 legacy overlay migration patch

Apply this to FE-010.

### Required migration audit output

Repo inspection must produce:

| Current path/file | Current role | Current event/command names | Canonical replacement | Decision | Adapter needed | Blocker |
|---|---|---|---|---|---|---|
| example legacy overlay file | plan UI | old_plan_ready | FE-004 + plan_ready | adapt/deprecate/block | yes/no | missing payload |

### Decision values

| Decision | Meaning |
|---|---|
| keep | already aligned with Shadow DOM/canonical contract |
| adapt | temporary adapter needed |
| deprecate | legacy-only; do not use for new work |
| block | cannot migrate safely until upstream contract exists |
| remove later | safe after replacement accepted |

### Migration-complete criteria

FE-010 is complete when:

- every legacy overlay entry point is listed
- every frontend event consumer is listed
- every frontend command sender is listed
- every picker/element-info UI path is listed
- every current UI state store/local flag is listed
- each item maps to keep/adapt/deprecate/block/remove later
- Shadow DOM target path is identified
- no new story is instructed to build on legacy overlay as source of truth

### Transitional rule

```text
Legacy overlay may remain temporarily for compatibility,
but new Complete LLM Mode work must target Shadow DOM and typed event/command contracts.
```

### Tests/audit checks

```markdown
| FE010-A-004 | Audit | all local lifecycle flags listed | complete map |
| FE010-A-005 | Audit | legacy command senders listed | complete map |
| FE010-A-006 | Audit | overlay-only picker path listed | decision assigned |
| FE010-I-002 | Integration | Shadow DOM path consumes canonical event | no legacy-only dependency |
```

---

## 15. FE story boundary clarification

Apply these boundaries:

### FE-004 vs FE-005

```text
FE-004 owns plan review, confirmation, and plan correction UI.
FE-005 owns clarification and recovery decision UI.
Both may render user decision surfaces, but they consume different backend event families.
```

### FE-006 vs FE-007

```text
FE-006 owns product output panels: recorded steps and generated code.
FE-007 owns diagnostics/debug evidence: trace, telemetry, rejection, and evidence references.
```

### FE-008 vs FE-010

```text
FE-008 owns the future picker/candidate UI contract.
FE-010 audits legacy picker/overlay paths and maps them to the new Shadow DOM contract.
```

---

## 16. Batch 06 patch acceptance criteria

Batch 06 is accepted after:

- FE-001 through FE-010 include source evidence tables.
- FE-001 through FE-010 include four-developer coordination blocks.
- FE-004 through FE-010 contain the missing PLAN-002 sections or are covered by this patch before implementation.
- FE-001 includes duplicate injection, navigation, cleanup, and error-boundary behavior.
- FE-002 includes out-of-order, stale, duplicate, reconnect, and malformed event behavior.
- FE-003 includes command idempotency/correlation/timeout behavior.
- FE-004 includes stale plan, correction pending, and revised plan backend-only rules.
- FE-005 includes option_selected semantics and recovery rejection behavior.
- FE-006 includes ordering, diagnostic_only, and no-code-before-recording behavior.
- FE-007 includes grouping, evidence, redaction, and summarization behavior.
- FE-008 includes candidate levels, warnings, and update_locator truth boundary.
- FE-009 includes hook naming pattern and non-interference rule.
- FE-010 includes concrete migration audit output and done criteria.

After this patch:

```text
EPIC-005 = planning-ready.
FE-001 through FE-010 = ready for repo inspection.
FE-001 through FE-010 = not ready for immediate implementation.
```
