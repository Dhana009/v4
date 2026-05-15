# PATCH-001 Batch 02 Backend Runtime Truth Story Corrections

**Type:** Planning Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** BE-002 through BE-012  
**Epic:** EPIC-001 Backend Runtime Truth  
**Reason:** Codex Batch 02 review found Batch 02 structurally strong but needing dependency and specificity patches before freezing.  
**Decision:** Patch Batch 02. Do not regenerate. Do not start implementation from Batch 02 until this patch is applied.  

---

## 1. Codex review result

Codex reviewed BE-002 through BE-012 using only the Tasks.md planning files.

Result:

```text
Confidence: High
All BE-002 through BE-012 are ready for repo inspection.
None are ready for immediate implementation.
Final decision: Patch Batch 02.
```

Reason:

```text
The story chain is logically ordered and structurally strong,
but several story headers under-declare dependencies,
and some command/event/schema/test details need tightening.
```

---

## 2. Patch goal

This patch makes Batch 02 consistent with the EPIC-001 dependency map and the Batch 01 v4 story standard.

Patch objectives:

1. Fix explicit dependency metadata in story headers.
2. Expand BE-002 canonical event coverage.
3. Expand BE-003 canonical command coverage.
4. Add story-specific edge/test improvements.
5. Clarify branch stories BE-011 and BE-012.
6. Avoid broad regeneration.

---

## 3. Header dependency corrections

Apply these dependency corrections to the story header of each file.

### BE-002

Current dependency should include:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001
```

No additional backend story dependency required.

### BE-003

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-002
```

Reason:

```text
BE-003 uses BE-002 rejection/event schema.
```

### BE-004

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-003
```

Reason:

```text
BE-004 active plan commands depend on command validation.
```

### BE-005

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-003, BE-004
```

Reason:

```text
BE-005 confirms the backend-owned active plan.
```

### BE-006

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-004, BE-005
```

Reason:

```text
BE-006 validates execution against confirmed active plan.
```

### BE-007

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-003, BE-004, BE-005
```

Reason:

```text
Correction command must be validated, applied to active plan, and blocked after confirmation/execution as needed.
```

### BE-008

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-002, BE-003
```

Reason:

```text
Recovery state needs runtime state, recovery events, and validated recovery commands.
```

### BE-009

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-006, BE-008
```

Reason:

```text
Recording uses validated execution evidence and unresolved-failure state.
```

### BE-010

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-002, BE-008, BE-009
```

Reason:

```text
Completion requires terminal state, no recovery blocker, recorded evidence, and run_completed event.
```

### BE-011

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-002, BE-003
```

Reason:

```text
Capability gap baseline needs state, typed gap event, and unsupported command/action rejection path.
```

### BE-012

Change dependencies to:

```text
Dependencies: SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-002, BE-003, BE-009, BE-010
```

Reason:

```text
Replay smoke needs replay commands/events plus recorded/terminal source data.
```

---

## 4. BE-002 event coverage patch

Add this section to BE-002 after “Event schema contract”.

```markdown
## Canonical event family coverage

BE-002 must cover every event family from SOURCE-001, either as implemented schema or explicitly deferred compatibility placeholder.

| Event family | P0 requirement | Notes |
|---|---|---|
| ready | schema or compatibility adapter | app/session ready |
| run_started | schema | run lifecycle starts |
| plan_ready | schema | active plan awaiting confirmation |
| clarification_needed | schema | missing user input |
| recovery_needed | schema | unresolved failure decision |
| step_validating | schema | operation validation starting |
| step_executing | schema | operation execution starting |
| step_recorded | schema | backend recording truth |
| step_failed | schema | failed step/operation |
| step_skipped | schema | explicit skip with reason |
| code_update | schema placeholder if BE-009/Codegen owns full payload | triggered by recorded children |
| replay_started | schema placeholder if BE-012 owns full payload | replay smoke |
| replay_result | schema placeholder if BE-012 owns full payload | replay outcome |
| run_completed | schema | terminal success only |
| session_state | schema or compatibility adapter | save/load/session state |
| capability_gap_recorded | schema placeholder if BE-011 owns full payload | unsupported capability |
```

Add tests:

```markdown
| BE002-C-007 | Contract | every canonical event registered | event registry | all listed or explicitly deferred | source coverage |
| BE002-C-008 | Contract | session_state payload | minimal session state | accepted/rejected by schema | session compatibility |
| BE002-C-009 | Contract | capability_gap_recorded placeholder | gap payload | accepted or delegated | gap event |
| BE002-C-010 | Contract | replay event placeholder | replay_started/result | accepted or delegated | replay event |
```

---

## 5. BE-003 command coverage patch

Add this section to BE-003 after “Command schema contract”.

```markdown
## Canonical command family coverage

BE-003 must cover every frontend-to-backend command from SOURCE-001.

| Command family | P0 requirement | Notes |
|---|---|---|
| run_steps / llm_run | validate | starts planning/run |
| confirmed | validate | confirmation gate |
| correction | validate | active plan correction |
| option_selected | validate | clarification/recovery choice |
| replay_step | validate | BE-012 consumes |
| replay_operation | validate | BE-012 consumes |
| replay_all | validate | BE-012 consumes |
| skip_step | validate | explicit reason required |
| stop_run | validate | non-terminal stop |
| save_session | validate or placeholder | persistence/session story may own full implementation |
| load_session | validate or placeholder | persistence/session story may own full implementation |
| update_locator | validate or placeholder | locator story may own full implementation |
```

Add tests:

```markdown
| BE003-U-007 | Unit | option_selected without pending option | invalid option | runtime_rejected | clarification/recovery safety |
| BE003-U-008 | Unit | save_session unsupported/malformed | command payload | typed rejection or placeholder accepted | session command coverage |
| BE003-U-009 | Unit | load_session unsupported/malformed | command payload | typed rejection or placeholder accepted | session command coverage |
| BE003-U-010 | Unit | update_locator missing target | missing step/operation | rejected | locator update safety |
```

---

## 6. BE-005 test patch

Add to BE-005 test matrix:

```markdown
| BE005-U-006 | Unit | confirm while clarification open | pending_clarification_id set | runtime_rejected | clarification blocks execution |
| BE005-U-007 | Unit | confirm while recovery open | unresolved_failure set | runtime_rejected | recovery blocks execution |
```

---

## 7. BE-006 cursor/detail patch

Add this section to BE-006 after “Execution contract schema”.

```markdown
## Cursor update rules

Cursor behavior:

| Situation | Cursor result |
|---|---|
| expected operation succeeds with backend evidence | advance to next operation |
| expected operation fails | cursor remains blocked and recovery opens |
| LLM claims success without backend evidence | cursor does not advance |
| wrong operation_id received | reject; cursor unchanged |
| wrong step_id received | reject; cursor unchanged |
| stale plan version received | reject; cursor unchanged |
| all operations in current step succeed | step may become recordable |
| current step recorded/skipped | advance to next step |
| no remaining confirmed steps | eligible for completion guard |

Add tests:

| BE006-U-007 | Unit | ordered step mismatch | step 2 op during step 1 | rejected; cursor unchanged | strict cursor |
| BE006-U-008 | Unit | cursor mismatch | wrong operation order | rejected | operation order |
| BE006-U-009 | Unit | failed op blocks cursor | expected op fails | recovery; cursor blocked | recovery safety |
```

---

## 8. BE-007 correction-semantics patch

Add this section to BE-007 after “Correction diff schema”.

```markdown
## Correction application semantics

Rules:

| Diff case | Required behavior |
|---|---|
| add operation | assign stable operation_id and order_index |
| update operation | preserve operation_id unless operation is semantically replaced |
| remove operation | require explicit reason |
| reorder operation | preserve ids, update order only |
| partial diff invalid | reject entire diff unless story explicitly supports partial apply |
| stale plan version | reject |
| correction after confirmation | reject unless future story explicitly supports this_and_following style split |
| LLM invalid schema first time | retry once through LLM policy |
| LLM invalid schema second time | fail closed / ask user |

Add tests:

| BE007-U-005 | Unit | partial diff failure | one invalid op in diff | reject entire diff | atomic correction |
| BE007-U-006 | Unit | reorder preserves ids | reorder operations | ids unchanged | identity |
| BE007-U-007 | Unit | invalid schema retry policy | invalid diff once/twice | retry once then fail closed | LLM schema safety |
```

---

## 9. BE-009 recording specificity patch

Add tests to BE-009:

```markdown
| BE009-U-006 | Unit | duplicate child IDs | recording children duplicate op id | rejected | child identity |
| BE009-U-007 | Unit | partial success then failure | one child success, one failed | parent not recorded | reconciliation |
| BE009-U-008 | Unit | ordered child evidence | children out of confirmed order | rejected or reordered by policy | codegen correctness |
```

Add edge case:

```text
recorded parent created while child order differs from confirmed execution contract
```

---

## 10. BE-010 completion specificity patch

Add this section to BE-010 after “Completion contract”.

```markdown
## Terminal-state check

Completion guard must evaluate:

| Object | Required terminal state |
|---|---|
| RunState | executing or equivalent completion-eligible state before transition |
| PlanState | confirmed or accepted terminal policy |
| StepState | recorded, skipped, cancelled/stopped, or terminal failed by explicit policy |
| OperationState | succeeded, skipped by policy, or terminal failed by explicit policy |
| RecoveryState | no unresolved recovery |
| ClarificationState | no pending clarification |
| RecordingState | required successful steps recorded |

If any required object is non-terminal, completion is rejected with `runtime_rejected`.

Add tests:

| BE010-U-007 | Unit | step planned but not recorded | one StepState.planned | rejected | no false completion |
| BE010-U-008 | Unit | child success but parent not recorded | operation succeeded, step not recorded | rejected | parent reconciliation |
| BE010-U-009 | Unit | terminal failed explicit policy | failed terminal marked accepted | allowed/rejected by explicit policy | failure semantics |
```

---

## 11. BE-011 branch clarification patch

Add this section to BE-011 near dependency map.

```markdown
## Branch story note

BE-011 is not a linear blocker for BE-012.

It is a side branch from the event/command layer:

```text
BE-001 + BE-002 + BE-003
→ BE-011 capability gap baseline
```

It supports trace and advanced-capability backlog. It should not delay recording/replay stories unless unsupported capability handling is part of their test path.
```

---

## 12. BE-012 replay mode patch

Add this section to BE-012 after “Replay smoke contract”.

```markdown
## Replay target modes

BE-012 has three target modes:

| Mode | Target fields | P0 behavior |
|---|---|---|
| replay_step | recorded_step_id | replay ordered children for one recorded step |
| replay_operation | recorded_step_id + operation_id | replay one child operation/check |
| replay_all | recorded_run_id/session_id | replay recorded steps in order, stop_on_error policy |

Mode rules:

- replay_step and replay_operation are distinct command paths.
- replay_operation must validate parent recorded_step_id.
- replay_all must not run live unrecorded steps.
- all modes check precondition before browser action.
- all modes emit replay_started and replay_result.
```

Add tests:

```markdown
| BE012-U-005 | Unit | replay while live execution active | RunState.executing | rejected or isolated by policy | replay separation |
| BE012-U-006 | Unit | replay_operation without parent | operation id only | rejected | parent identity |
| BE012-U-007 | Unit | replay_all stop_on_error | one failed recorded step | stops or reports by policy | replay control |
```

---

## 13. Four-developer coordination patch

For each BE-002 through BE-012 story, strengthen the four-developer section with one story-specific line:

### BE-002

```text
DEV-3 can build typed rendering only against canonical event fixtures from this story.
DEV-4 can assert lifecycle only after event capture supports these names.
```

### BE-003

```text
DEV-3 command buttons must send canonical command payloads, not mutate UI state.
DEV-4 should test rejected commands as first-class failures, not generic errors.
```

### BE-004

```text
DEV-2 must treat generated plans as proposals until backend stores active plan.
DEV-3 must render backend active plan, not local plan reconstruction.
```

### BE-005

```text
DEV-2 must not trigger tools before confirmation.
DEV-4 must prove no browser action occurs before confirmation.
```

### BE-006

```text
DEV-2 may propose operation; backend contract validator decides allow/block.
DEV-4 must test wrong-step and wrong-operation rejection.
```

### BE-007

```text
DEV-2 owns diff schema proposal quality, but backend owns apply/reject.
DEV-3 must show revised plan only after backend accepts correction.
```

### BE-008

```text
DEV-2 may diagnose failure, but backend owns recovery state.
DEV-3 must render recovery options from backend payload only.
```

### BE-009

```text
DEV-3 Recorded/Code tabs consume backend recorded payloads.
DEV-4 must verify recorded parent/child order.
```

### BE-010

```text
DEV-3 final success state comes only from run_completed.
DEV-4 must test false-success blockers.
```

### BE-011

```text
DEV-2 must not hallucinate support for unsupported capability.
DEV-4 can test expected capability_gap_recorded outcomes.
```

### BE-012

```text
DEV-3 replay controls send replay commands only.
DEV-4 validates replay smoke and precondition failure artifacts.
```

---

## 14. Patch acceptance criteria

Batch 02 is accepted after:

- all header dependencies match this patch
- BE-002 includes canonical event family coverage
- BE-003 includes canonical command family coverage
- BE-006 includes cursor update rules
- BE-007 includes correction semantics/retry-once rule
- BE-010 includes terminal-state check
- BE-012 includes replay target modes
- story-specific four-developer coordination is added

After this patch, BE-002 through BE-012 can remain:

```text
Ready for repo inspection
Not ready for immediate implementation
```
