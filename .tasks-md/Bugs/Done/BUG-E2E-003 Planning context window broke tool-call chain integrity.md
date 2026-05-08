# BUG-E2E-003 Planning context window broke tool-call chain integrity

Status: Done
Sprint: Sprint 3
Type: Bug
Severity: P0
Owner: Context Manager / E2E
Priority: P0
Started: 2026-05-08 21:23 IST

## Expected

Purpose-specific planning windows must never preserve an assistant tool-call message without its matching tool response.

## Actual

`visible_assertion_flow` failed with OpenAI `BadRequestError`:

```text
An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'
```

Artifact:

`test-results/autoworkbench-e2e/visible_assertion_flow-20260508-203431-46422`

## Root cause

`step_plan_normalizer` windowing preserved the latest assistant turns by role, which could keep an older assistant tool-call message while dropping its tool response.

## Fix plan

- Exclude tool-calling assistants from generic recent-turn preservation.
- Keep only complete latest tool chains.

## Verification

- Focused tests:
  - `python -m pytest tests/test_context_manager.py -q`
- Paid E2E:
  - `python -m pytest tests/e2e/test_visible_assertion_flow.py -q -s`
- Result:
  - context window now preserves only complete tool-call chains
  - `visible_assertion_flow` passed after the fix with `0` LLM calls
