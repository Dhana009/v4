# Sprint 6 Cluster 12: Final Complete LLM Mode Acceptance and Integration Validation

## Cluster Goal

Prove that **Complete LLM Mode as specified** works end-to-end.

This is the closure cluster. It should not introduce major new product behavior. It should validate, harden, fix small integration gaps, update docs/task board, and produce final acceptance evidence.

The scenario spec defines Complete LLM Mode as:
broad intent → clarification → page/section context → recommendation/plan → revision → backend validation → safe execution → recording → codegen → recovery/stop.

## Cluster Scope

**10 stories:**
- S6-1201: Complete LLM Mode final requirement matrix review
- S6-1202: Full cheap regression suite
- S6-1203: Complete LLM Mode local fixture E2E suite
- S6-1204: Real LLM contract probes
- S6-1205: Controlled paid browser E2E acceptance
- S6-1206: Coverage report and gap handling
- S6-1207: Architecture drift audit
- S6-1208: Task board and documentation closure
- S6-1209: Final handoff document
- S6-1210: Final push/merge readiness gate

## Key Invariants

1. **No major new features** — Cluster 12 is validation, not development
2. **Evidence-backed statuses** — every Complete LLM Mode requirement has proof or explicit non-Done status
3. **Cheap gates first** — paid E2E only after local/cheap tests pass
4. **Fail-fast on drift** — architecture invariants checked before closure
5. **Clean closure** — task board, docs, and repo state accurately reflect final Sprint 6 state

## Allowed Implementation Modules

Cluster 12 (minimal product code, mostly tests/docs):

```
tests/e2e/** — final acceptance gaps only
.tasks-md/** — final matrix and closure docs only
docs/** — final handoff and architecture summary
```

## Forbidden

- No broad new feature development
- No paid E2E before cheap/local gates
- No unredacted secrets/artifacts committed
- No force push
- No fake Done
- No skipped/xfail tests to hide failures
- No frontend trace mutating runtime state
- No AGENTS.md/.DS_Store commits

## Hard Stops (Paid E2E)

- No artifacts → blocked
- Unredacted secrets → blocked
- LLM emits execution success → blocked
- Browser action before confirmation → blocked
- run_completed while recovery open → blocked
- code_update before step_recorded → blocked
- raw_response/tool-call invariant error → blocked
- Unbounded thinking loop → blocked

## Definition of Done

✅ Final requirement matrix has evidence-backed statuses.
✅ Cheap regression suite passes.
✅ Local fixture E2E suite passes.
✅ Real LLM probes pass or blockers documented.
✅ Controlled paid E2E passes where approved.
✅ Coverage target met or exceptions explicitly approved.
✅ Architecture drift audit passes.
✅ Task board accurately reflects final state.
✅ Final handoff exists.
✅ Repo is clean/push-ready.
