# S6-1108: Cluster 11 Observability Integration Proof

## Objective

Prove the observability layer works across representative Complete LLM Mode flows.

## Acceptance Criteria

- [ ] Page recommendation flow produces page intelligence and recommendation artifacts
- [ ] Plan correction flow produces plan_diff trace
- [ ] Recovery flow produces failure-context and attempted recovery trace
- [ ] Replay repair flow produces replay/repair/version trace
- [ ] Trace events are correlated
- [ ] Artifact manifest lists expected files with hashes
- [ ] Redaction report exists
- [ ] LLM calls artifact links to trace call_id
- [ ] Failure summary names layer owner and next legal action
- [ ] All required artifacts present in bundle

## Required Test Flows

1. Page recommendation flow
2. Plan correction flow
3. Recovery flow
4. Replay repair flow
5. Paid-test policy verification

## Integration Points

- Verifies S6-1101 (trace event model)
- Verifies S6-1102 (lifecycle trace)
- Verifies S6-1103 (LLM calls)
- Verifies S6-1104 (artifact bundle)
- Verifies S6-1105 (redaction)
- Verifies S6-1106 (failure context)
- Verifies S6-1107 (trace export)

## Dependencies

- All S6-110x stories must be complete before this story

## Notes

This is the proof story for Cluster 11. Cluster 11 is Done only when this story passes.
