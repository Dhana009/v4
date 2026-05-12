# S6-1103: LLM Call Artifact Completeness

## Objective

Make all controller-owned LLM calls observable in llm-calls.json artifact.

## Acceptance Criteria

- [ ] llm-calls.json artifact written on every LLM call (success and failure)
- [ ] All required fields captured per call
- [ ] Redaction applied before artifact write
- [ ] Token usage recorded when available
- [ ] Schema violations fail test, not silently
- [ ] Unit tests verify artifact creation on success/failure
- [ ] Contract tests verify mandatory fields present
- [ ] Regression tests on S5 llm-calls behavior

## llm-calls.json Fields

call_id, purpose, model, model_class, prompt_pack_id, prefix_hash, context_level, skills_loaded, skill_levels, exposed_tool_names, safe_tool_schema_summary, assistant_text, tool_call_names, safe_tool_args, finish_reason, usage, latency_ms, timestamp_epoch, failure_type, failure_message, timestamp

## Constraints

- No raw API keys or auth tokens
- No raw credentials
- No raw full DOM unless explicit redacted artifact
- No unbounded prompt dumps by default
- Prefix hash tracks prompt input without storing full prompt

## Integration Points

- Works with S6-1101 (trace event model)
- Works with S6-1104 (artifact bundle)
- Works with S6-1105 (redaction policy)
- Feeds S6-1107 (trace export)
