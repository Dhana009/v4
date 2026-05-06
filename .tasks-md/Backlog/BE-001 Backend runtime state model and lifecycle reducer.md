# BE-001 Backend runtime state model and lifecycle reducer

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-001 Backend Runtime Truth  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001  
**Blocks:** BE-002, BE-003, BE-004, BE-005, BE-006, BE-010, FE lifecycle rendering, E2E lifecycle assertions  
**Version:** v4 after Codex Batch 01 reviews  

---

## 1. Product contribution

This story gives AutoWorkbench the backend runtime state foundation required for Complete LLM Mode.

It contributes to the final product by making this user workflow trustworthy:

```text
user intent
→ backend creates/holds runtime state
→ LLM proposes plan only
→ user reviews plan
→ backend validates confirmation
→ backend executes safely
→ backend records actual evidence
→ backend decides completion
```

Without this story, later features cannot be trusted because runtime state may again come from:

- LLM prose
- frontend local flags
- legacy overlay state
- scattered globals
- last-successful-action heuristics

---

## 2. Direct vs indirect downstream dependency note

### Directly blocked by BE-001

These cannot safely proceed to implementation without BE-001’s runtime state model or an approved mock contract:

```text
BE-002 Canonical backend event emitter and schema validation
BE-003 Backend command validation and typed rejection
BE-004 Active plan store and plan_ready ownership
BE-005 Plan confirmation gate
BE-006 Confirmed execution contract validator
BE-010 Completion guard and run_completed contract
DEV-3 real frontend lifecycle rendering
DEV-4 real lifecycle E2E assertions
```

### Indirect downstream consumers

These rely on BE-001 through later backend stories and can be planned now, but should not assume final implementation details:

```text
BE-007 Structured correction diff validation and application
BE-008 Backend recovery state ownership
BE-009 Backend-owned recording builder
BE-011 Capability gap event baseline
BE-012 Replay smoke contract baseline
EPIC-008 Recording/Codegen deeper work
EPIC-009 Trace/Observability
```

### Parallel-safe work

These can continue with mocks:

```text
DEV-2 LLM schema/policy planning using backend validator assumptions
DEV-3 Shadow DOM shell using mock canonical events
DEV-4 fixture/harness skeleton and artifact capture
```

---

## 3. P0 persistence expectation

For BE-001:

```text
P0 runtime state may be in-memory first unless current repo already has an accepted persistence path.
```

Reason:

```text
BE-001 is about runtime truth and transition validation first. Full durable persistence should not block P0 unless current repo architecture already supports it cleanly.
```

Future persistence impact:

```text
State objects must be structured so active session persistence, save/load session, replay archive, and trace persistence can be added later without changing ownership semantics.
```

Forbidden:

```text
Do not hardcode new hidden global paths.
Do not mix runtime state persistence into frontend/local UI state.
Do not block BE-001 on full production persistence unless repo inspection proves it is already required.
```

---

## 4. Step/operation cardinality and reconciliation

BE-001 defines the parent/child lifecycle model.

Rules:

```text
One StepState may contain one or more OperationState children.
Each OperationState belongs to exactly one StepState.
Children have explicit order under the parent StepState.
A parent StepState cannot become recorded from only one loose last action.
```

Parent reconciliation:

| Child operation situation | Parent StepState result |
|---|---|
| all required children succeeded | may become recorded |
| one required child failed | recovery_pending or failed |
| optional child skipped with reason | may continue if policy allows |
| required child skipped with reason | parent skipped only if explicit user/backend skip path allows |
| child success evidence missing | cannot record |
| child order differs from confirmed plan | reject/recovery; do not record |
| duplicate operation_id | reject before execution/recording |
| some children succeeded and one failed | partial evidence preserved, parent not recorded until resolved |

This protects recording/codegen from being built from `last_successful_action`.

---

## 5. Repo-inspection report template

Codex must report in this format:

```markdown
# Repo Inspection Report — BE-001

## 1. Files inspected
- ...

## 2. Current behavior observed
- ...

## 3. Current ownership map
| Concern | Current file/function/module | Notes |
|---|---|---|
| lifecycle state | ... | ... |
| active plan | ... | ... |
| command handling | ... | ... |
| event emission | ... | ... |
| recording | ... | ... |
| replay | ... | ... |

## 4. Existing tests found
- ...

## 5. Source alignment check
| Source rule | Current implementation status | Gap |
|---|---|---|

## 6. Proposed narrow implementation path
- ...

## 7. Tests to add first
- ...

## 8. Files likely to change
- ...

## 9. Files explicitly not to change
- ...

## 10. Risks / blockers
- ...

## 11. Ready for implementation?
Yes/No, with reason.
```

---

## 6. Codex execution summary

First Codex task for BE-001 should be read-only:

```text
Read BE-001, SOURCE-001, PLAN-002, PLAN-005, EPIC-001, and required skills.
Do not edit code.
Inspect repo runtime/state ownership.
Report current files, lifecycle ownership, state storage, existing tests, risks, and narrow implementation plan using the repo-inspection report template.
Do not implement until review approves the repo-inspection report.
```

---

## Note

This v4 patch intentionally contains only the final refinement sections. It should be merged over the existing BE-001 v3 content or used to replace the sections with the same headings.
