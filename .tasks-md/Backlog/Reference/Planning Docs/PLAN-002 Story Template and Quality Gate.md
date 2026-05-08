# PLAN-002 Story Template and Quality Gate

**Type:** Planning Control  
**Status:** Planning  
**Priority:** P0  
**Owner:** Planning Brain  
**Applies To:** All implementation stories  
**Version:** v4 after Codex Batch 01 reviews  

---

## 1. Purpose

A story must be self-explanatory to a fresh Codex worker with no prior chat context.

A story must answer:

```text
What am I building?
Why does it matter to the final product?
Which source rule requires it?
Which architecture decision does it enforce?
Who depends on it?
What can run in parallel?
What tests prove it?
When must I stop?
```

The quality goal is **high-signal context**: product contribution, source evidence, architecture boundary, dependencies, test proof, and stop rules.

---

## 2. Required story sections

Every story must contain:

1. Story identity
2. Product contribution
3. Final product workflow supported
4. System role
5. Source evidence table
6. Architecture decision
7. Dependency map
8. Direct vs indirect dependency note
9. Four-developer coordination
10. What upstream stories unlock for this story
11. What this story unlocks downstream
12. Implementation contract
13. P0 persistence expectation where relevant
14. Schema/state/event/command contract
15. Flow contract
16. Test matrix
17. Negative/edge/boundary cases
18. Acceptance criteria
19. Required evidence
20. Required skills
21. Allowed areas
22. Forbidden areas
23. Repo-inspection requirement
24. Repo-inspection report template
25. Stop conditions
26. Codex comprehension checklist
27. Codex execution summary

---

## 3. Direct vs indirect dependency rule

Every story must distinguish between:

```text
Direct blockers:
Stories/workstreams that cannot reasonably proceed until this story exists.

Indirect downstream consumers:
Stories/workstreams that eventually rely on this story through the epic dependency chain, but may be able to plan or partially work with mocks.
```

Required format:

| Dependency level | Items | Meaning |
|---|---|---|
| Direct blockers | ... | Cannot proceed safely without this story |
| Indirect downstream consumers | ... | Eventually rely on this story but may plan/mock now |
| Parallel safe with mocks | ... | Can proceed if they do not assume final implementation |

This prevents over-blocking all four developers while still making dependencies explicit.

---

## 4. Step/operation cardinality rule

Stories touching execution, recording, codegen, replay, or completion must use this relationship unless repo inspection proves a better source-backed model:

```text
One StepState may contain one or more OperationState children.
Each OperationState belongs to exactly one StepState.
A StepState is recorded only after required child operations/checks are terminal in the accepted way.
```

Required child reconciliation rules:

| Case | Parent StepState result |
|---|---|
| all required children succeeded | recorded candidate |
| one required child failed | recovery_pending or failed |
| optional child skipped with reason | may continue if policy allows |
| required child skipped with reason | skipped only if explicit user/backend path allows |
| child success evidence missing | cannot record |
| child order differs from confirmed plan | reject or recovery, do not record |
| duplicate operation_id | reject before execution/recording |

This prevents parent recorded status from being derived from one loose last action.

---

## 5. P0 persistence expectation

Unless a story explicitly says otherwise:

```text
P0 persistence may be in-memory first if current repo does not already have an accepted persistence path.
```

However:

- state model must be structured so persistence can be added later
- recorded steps/codegen/replay archive stories may have stricter persistence requirements
- do not hardcode hidden global paths without source support
- do not block P0 runtime truth on full production persistence unless PRD/story requires it

Required format for stories involving state:

```markdown
## P0 persistence expectation

For P0, this story requires [in-memory / persisted / TBD after repo inspection].
Reason:
...
Future persistence impact:
...
```

---

## 6. Standard rejected-transition payload

BE-002 and BE-003 must align around a standard rejection shape. Stories can refine exact fields after repo inspection.

Minimum payload:

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

Do not expose only free-form error strings.

---

## 7. Repo-inspection report template

Any story marked “ready for repo inspection” must tell Codex to report in this format:

```markdown
# Repo Inspection Report — <Story ID>

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

No implementation should start until this report is reviewed for stories that require repo inspection.

---

## 8. Ready gate

Move story to `Ready` only if:

- product contribution is clear
- dependency map is clear
- direct vs indirect dependencies are clear
- four-developer coordination is clear
- source evidence table exists
- architecture decision is explicit
- schema/contract details exist where relevant
- tests are concrete
- stop conditions are exact
- repo-inspection report format is included where needed
- Codex can inspect repo without extra chat context
