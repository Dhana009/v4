# S6-1101: Structured Trace Event Model Completion

## Objective

Create/complete the structured trace event model for Complete LLM Mode.

## Acceptance Criteria

- [ ] Trace event schema defined with all required fields
- [ ] No optional fields without explicit reason/absence handling
- [ ] Event model is serializable and bounded
- [ ] Unit tests verify field requirements
- [ ] Contract tests verify trace cannot mutate runtime state
- [ ] Unknown event type becomes visible diagnostic, not silent failure
- [ ] Module: `runtime/trace_events.py`
- [ ] Tests: `tests/test_trace_events.py`

## Required Fields

run_id, session_id, plan_id, plan_version, step_id, operation_id, phase, event_type, status, reason, duration_ms, llm_purpose, context_level, estimated_tokens, actual_tokens, artifact_path, correlation_id, parent_event_id, timestamp_epoch

## Event Type Enumeration

user_input_received, intent_classified, clarification_needed, page_analysis_requested, page_summary_ready, recommendation_ready, plan_ready, plan_diff_proposed, plan_diff_validated, plan_diff_applied, plan_confirmed, execution_started, operation_started, operation_completed, operation_failed, recovery_needed, recovery_attempted, recovery_succeeded, step_recorded, code_update, replay_started, replay_result, run_completed, runtime_rejected, capability_gap_recorded

## Constraints

- No runtime truth mutation from trace
- No frontend lifecycle inference baked into trace schema
- No raw secrets in any trace field
- No unbounded payload dumps (max 1KB reason field)
- Trace is read-only from runtime perspective

## Dependencies

- Cluster 11 governance (SPRINT-006-CLUSTER-11-TRACE-OBSERVABILITY.md)
