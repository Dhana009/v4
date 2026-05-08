# INT-TOOL-001 Fix token report top-source calculation

Status: Done
Sprint: Sprint 3
Type: Story
Owner: Runtime / Evidence
Priority: P0
Started: 2026-05-08 19:56 IST

## Problem

The token diagnosis found tool_schema_tokens are the actual largest aggregate bucket, but runtime/token_report.py does not include tool_schema_tokens in top_token_source winner logic.

This hides the real source of cost.

## Source / architecture rule

- runtime/token_report.py
- runtime/telemetry.py
- Complete LLM Mode Runtime Policy Spec
- Sprint 3 token diagnosis report

## Scope

Update token report logic so top_token_source includes:

- system_prompt_tokens
- skill_tokens
- tool_schema_tokens
- message_history_tokens
- dom_or_tool_result_tokens

## Out of scope

- Changing tool exposure behavior
- Changing LLM call behavior
- Changing E2E flow behavior

## Required tests

- token report selects tool_schema_tokens as top source when it is largest
- token report still handles missing fields safely
- existing token report tests still pass

## Acceptance criteria

- token-report.json correctly reports tool_schema_tokens as top source when applicable
- no product behavior change
- focused token report tests pass

## Cost-aware verification plan

Run only token report unit tests and py_compile.
No E2E required for this ticket.

## Evidence

- `python -m py_compile runtime/token_report.py` -> passed
- `python -m pytest tests/test_token_report.py -q` -> 20 passed

## Implementation summary

- `tool_schema_tokens` is now included in `top_token_source` winner logic
- top-source comparison now covers system, skill, tool schema, history, and DOM/tool-result buckets
- missing token fields still default safely to zero during aggregation

## Notes

Measurement correctness comes first.
