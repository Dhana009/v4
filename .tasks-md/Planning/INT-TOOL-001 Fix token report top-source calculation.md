# INT-TOOL-001 Fix token report top-source calculation

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: Runtime / Evidence
Priority: P0

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

To be filled during implementation.

## Notes

Measurement correctness comes first.
