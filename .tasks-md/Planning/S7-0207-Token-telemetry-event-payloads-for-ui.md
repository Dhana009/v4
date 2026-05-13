# S7-0207 Token/Telemetry Event Payloads for UI

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0207  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `02_LLM_RUNTIME.md` (token budgets and telemetry).
2. **Frontend UI Spec** — Trace tab must show token usage.
3. **Cluster 2 Goal** — Telemetry exposed safely to frontend.

---

## Objective

Expose safe token/model/purpose telemetry to frontend via `token_report` event so UI can show costs and model usage without exposing secrets. Today, telemetry collected internally but not emitted to frontend. After S7-0207, frontend receives `token_report(purpose, model_class, input_tokens, output_tokens, estimated_cost)` events.

---

## Tests First

### Unit Tests

**Test: Token count extraction**
- Given LLM response with usage info, extract input/output token counts.
- Handle missing usage (gracefully return 0 or estimate).

**Test: Cost estimation**
- Given model_class and token counts, estimate cost.
- Formula: (input_tokens * input_rate + output_tokens * output_rate) / 1000.

### Contract Tests

**Test: token_report payload**
- Fields: purpose (str), model_class (str), input_tokens (int), output_tokens (int), estimated_cost (float), timestamp (ISO).
- Optional: tool_calls (int), reasoning_tokens (int).
- No secrets, no prompts, no LLM output text.

### Integration Tests

**Test: LLM call → token_report event**
- Call any LLM purpose.
- Verify token_report event emitted with correct counts.

### Negative Tests

**Test: Missing token info**
- LLM response missing usage.
- token_report still emitted with estimated values (not crash).

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `runtime/event_contracts.py`
  - Add: `TokenReport` event class.

- **Modify:** `runtime/telemetry.py`
  - Add: `emit_token_report()` function.
  - Safe extraction of token info (no prompt dump).

- **Modify:** `runtime/llm_runtime_controller.py` (thin seam)
  - After LLM call, emit token_report event.

- **Modify:** `server.py` or `ws/router.py`
  - Route token_report events to frontend.

- **New tests:** `tests/test_token_report_event.py`

### Forbidden Changes

- No prompt text in events.
- No API keys or secrets.
- No LLM output text.

---

## Acceptance Criteria

✅ **All tests green.**
✅ **Token counts accurate.**
✅ **Cost estimation correct.**
✅ **No secrets exposed.**
✅ **Evidence: test file, commits, regression green.**

---

## Stop Conditions

- ❌ Regression failure.
- ❌ Secrets in event payload.
- ❌ Prompt text leaked.

