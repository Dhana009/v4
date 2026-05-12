# S6-1106: Failure Context Artifact

## Objective

Every failed run/test produces a compact, actionable failure context.

## Acceptance Criteria

- [ ] failure-context.json exists for every failed run
- [ ] All required fields populated for diagnostic value
- [ ] Layer owner classification works
- [ ] Evidence refs point to relevant artifacts
- [ ] Attempted recoveries listed
- [ ] Next legal actions clear
- [ ] No huge raw logs (< 10KB summary)
- [ ] No full DOM dump by default
- [ ] No secrets in failure context

## Failure Context Fields

run_id, session_id, scenario_name, test_name, failed_stage, error_type, expected, actual, layer_owner, evidence_refs, attempted_recoveries, last_backend_event, last_frontend_state, last_llm_call_id, artifact_paths, next_legal_actions, summary, timestamp

## Constraints

- No huge raw logs
- No full DOM dump by default
- No raw secrets
- Failure context is diagnostic, not runtime state
- Evidence refs are actionable pointers

## Integration Points

- Works with S6-1101 (trace events)
- Works with S6-1102 (lifecycle trace)
- Works with S6-1104 (artifact bundle)
- Works with S6-1105 (redaction)
- Feeds S6-1107 (trace export)
