# EPIC-001 Backend Runtime Truth

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Capability:** Backend Runtime Truth  
**Version:** v4 after Codex Batch 01 reviews  

---

## 1. Product contribution

This epic gives AutoWorkbench the backend truth layer required for Complete LLM Mode.

Final user value:

```text
User can trust that a reviewed/confirmed plan is the only thing executed,
that execution evidence is real,
that failures block completion,
and that generated Playwright code reflects what actually happened.
```

Without this epic:

- LLM could imply execution success.
- Frontend could infer completed state.
- Plan correction could drop/reorder operations.
- Recording could be built from weak heuristics.
- Codegen/replay would not be trustworthy.

---

## 2. Story dependency map

| Story | Purpose | What BE-001 unlocks for it | Depends on | Blocks |
|---|---|---|---|---|
| BE-001 | Runtime state/reducer | Foundation story | SOURCE, EPIC | BE-002 to BE-012, frontend lifecycle rendering |
| BE-002 | Event emitter/schema | Gives source state transitions that events expose | BE-001 | FE rendering, E2E event capture |
| BE-003 | Command validation | Gives current state to validate commands against | BE-001, BE-002 | confirmation/correction/replay commands |
| BE-004 | Active plan store | Gives RunState/PlanState relationship and version state | BE-001, BE-003 | BE-005, BE-006, BE-007 |
| BE-005 | Confirmation gate | Gives plan_review/executing transition boundary | BE-004 | BE-006, LLM Mode execution |
| BE-006 | Execution contract | Gives step/operation state and cursor foundation | BE-004, BE-005 | BE-009, E2E execution tests |
| BE-007 | Correction diff validation | Gives plan state/version semantics | BE-004, BE-005 | correction flow, LLM plan-diff story |
| BE-008 | Recovery state | Gives recovery/failure lifecycle shape | BE-001, BE-002, BE-003 | completion guard, E2E recovery |
| BE-009 | Recording builder | Gives operation terminal success evidence shape | BE-006, BE-008 | codegen, recorded UI |
| BE-010 | Completion guard | Gives terminal state model | BE-001, BE-008, BE-009 | run_completed, frontend final state |
| BE-011 | Capability gap event | Gives capability_gap state/event compatibility | BE-002, BE-003 | advanced capability backlog |
| BE-012 | Replay smoke | Gives replay/recording state separation | BE-009, BE-010 | robust replay P1 |

---

## 3. Direct vs indirect dependency note

### Directly blocked by BE-001

These need BE-001’s runtime state model before implementation can be safe:

```text
BE-002 Event emitter/schema
BE-003 Command validation
BE-004 Active plan store
BE-005 Confirmation gate
BE-006 Execution contract
BE-010 Completion guard
DEV-3 real frontend lifecycle rendering
DEV-4 real lifecycle E2E assertions
```

### Indirect downstream consumers of BE-001

These rely on BE-001 through later backend contracts and can be planned now, but should not assume final implementation details:

```text
BE-007 Correction diff validation
BE-008 Recovery state ownership
BE-009 Recording builder
BE-011 Capability gap event
BE-012 Replay smoke
EPIC-008 Recording/Codegen deeper work
EPIC-009 Trace/Observability
```

### Parallel safe work with mocks

These can proceed in parallel only with explicit mock contracts:

```text
DEV-2 LLM Runtime Controller policy/schema planning
DEV-3 Shadow DOM shell using mock canonical events
DEV-4 fixture/harness skeleton and artifact capture
```

Do not let parallel work invent final backend state/event truth.

---

## 4. Step/operation cardinality and reconciliation

This epic uses the shared rule from PLAN-002:

```text
One StepState may contain one or more OperationState children.
Each OperationState belongs to exactly one StepState.
A StepState can be recorded only after required child operations/checks are terminal in the accepted way.
```

Consequences:

- BE-006 must validate operation order/identity against confirmed children.
- BE-009 must build recorded parent/child output from child evidence, not last action.
- BE-010 must complete only after parent/child reconciliation is done.
- BE-012 must replay recorded children, not guessed operations.

---

## 5. P0 persistence expectation

For EPIC-001:

```text
P0 runtime state may be in-memory first unless current repo already has an accepted persistence path.
```

But:

- recording/codegen/replay archive stories may require persistence or saved artifacts
- state objects must be structured enough for later persistence
- no hardcoded hidden global paths should be added without source support
- do not block P0 backend truth on full production persistence unless a story explicitly requires it

---

## 6. Standard rejected-transition payload

BE-002 and BE-003 must align on the shape below unless repo inspection proves a safer existing pattern.

```json
{
  "type": "runtime_rejected",
  "run_id": "run_123",
  "plan_id": "plan_456",
  "plan_version": 2,
  "step_id": "step_001",
  "operation_id": "op_001",
  "rejection_code": "CONFIRMATION_REQUIRED",
  "message": "Execution cannot start before the active plan is confirmed.",
  "current_state": {
    "run_status": "plan_review",
    "plan_status": "awaiting_confirmation",
    "step_status": "planned",
    "operation_status": "planned"
  },
  "attempted_transition": {
    "from": "plan_review",
    "to": "executing",
    "command": "action_click"
  },
  "required_next_action": "confirmed",
  "recoverable": true,
  "evidence_ref": "trace/runtime/run_123/rejections/001.json"
}
```

---

## 7. Repo-inspection output expectation

Backend stories that are not ready for immediate implementation must produce a repo-inspection report before coding.

Use the template in `PLAN-002`.

Minimum required inspection for EPIC-001 stories:

- current lifecycle owner
- current plan/step/operation storage
- current event emission sites
- current command handling path
- current recording/replay storage
- current tests
- proposed narrow file/module plan
- ready-for-implementation decision
