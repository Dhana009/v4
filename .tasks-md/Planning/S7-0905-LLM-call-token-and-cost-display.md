# S7-0905 — LLM Call, Token, and Cost Display

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0901]

---

## Objective

Display LLM call telemetry in Trace tab or detail row. Show call_id, purpose, model_class, provider model if available, token estimate/actual, cached tokens, cost estimate. No raw prompts or API keys. Missing usage shows safe fallback.

After S7-0905:
- LLM call telemetry renders without prompt dump
- Token and cost summary computed from backend telemetry
- No raw prompts/API keys/secrets visible
- LLM call failure visible as trace evidence
- Missing telemetry shows safe "unavailable" state

---

## Source Rules

- PRD-07-AGENT-004: LLM call telemetry structure
- PRD-02-LLM-RUNTIME-003: Token attribution and cost tracking
- GOV-S7-C0-009: No raw secrets/prompts in frontend

---

## Tests First

### Unit Tests

```python
test_llm_telemetry_from_trace_event()  # PRD-07-AGENT-004
test_token_summary_computed()  # PRD-02-LLM-RUNTIME-003
test_cost_estimate_computed()  # PRD-02-LLM-RUNTIME-003
test_telemetry_no_raw_prompts()  # GOV-S7-C0-009
```

### Component Tests

```python
test_llm_telemetry_row_renders()  # PRD-07-AGENT-004
test_token_count_displayed()  # PRD-02-LLM-RUNTIME-003
test_cost_displayed()  # PRD-02-LLM-RUNTIME-003
test_missing_telemetry_safe()  # PRD-07-AGENT-004
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/trace/LLMTelemetryRow.jsx (new)
- tests/test_frontend_artifacts.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/telemetry.py
- frontend_new_design_prototype/
```

---

## Stop Conditions

Stop if:

- Telemetry data not available in backend trace
- Coverage below 95%

