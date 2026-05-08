# INT-OBS-001 LLM call and token telemetry report

Status: Done
Sprint: Sprint 3
Type: Story
Owner: Backend / LLM Runtime
Priority: P0

## Source docs

- Complete LLM Mode Runtime Policy Spec
- PRD v2.3 LLM Runtime
- PRD v2.3 Build Roadmap and Acceptance
- Sprint 3 cost optimization plan

## Problem / Goal

We need local visibility into LLM usage.

OpenAI dashboard shows high token usage, but AutoWorkbench does not yet provide a per-run/per-test breakdown of:

- number of LLM calls
- model used
- purpose used
- estimated input tokens
- output tokens when available
- system prompt tokens
- skill tokens
- tool schema tokens
- message/history tokens
- DOM/tool-result tokens
- largest call
- total tokens per flow

Without this report, token optimization is guesswork.

## Scope

Add a local telemetry report for LLM calls.

The report should be available after E2E/regression runs and should include enough detail to compare before/after token optimization.

Minimum fields:

- run_id
- test_name if available
- call_id
- purpose
- model
- estimated_input_tokens
- actual_input_tokens if available
- output_tokens if available
- total_tokens if available
- system_prompt_tokens
- skill_tokens
- tool_schema_tokens
- message_history_tokens
- dom_or_tool_result_tokens
- context_level
- skills_loaded
- tools_exposed_count
- largest_call marker
- timestamp / duration_ms

## Out of scope

- Full Trace UI redesign
- OpenAI billing API integration
- Multi-model routing
- Hard token budget enforcement

## Required tests

- Unit test that telemetry record includes purpose/model/token fields.
- Unit test that skill/system tokens are counted separately from history/tool tokens.
- Unit test that an E2E-style run can emit an aggregate token report.
- Regression test that missing token fields do not crash the run.

## Acceptance criteria

- Running current 5 E2E tests produces a local token/call report or artifact.
- Report shows total call count per test/run.
- Report shows total estimated input tokens per test/run.
- Report identifies largest prompt.
- Report separates system/skill/tool/history/DOM token categories where possible.
- Existing 5 E2E tests still pass.

## Key implementation constraint

`ModelCallTelemetry` in `runtime/telemetry.py` does not currently carry:

- system_prompt_tokens
- skill_tokens
- tool_schema_tokens
- message_history_tokens
- dom_or_tool_result_tokens

It has `skill_count` and `estimated_message_tokens`, but no category breakdown.

INT-OBS-001 must extend `ModelCallTelemetry` and wire `SkillManager.analyze()` results, especially `estimated_total_skill_tokens`, into the telemetry record.

This is the core implementation work for this story.

## Report format

Telemetry emission alone is not enough.

The required report format is:

- parse `[LLM_TELEMETRY]` lines from backend stdout
- produce a structured JSON artifact named `token-report.json`
- place it in the E2E artifact directory
- include a concise summary table at E2E run end

A raw `[LLM_TELEMETRY]` line in `backend.stdout.log` is not sufficient by itself.

## Evidence

Phase 0 measurement foundation complete.
Live E2E telemetry now records per-call token categories for system, skill, tool schema, history, and DOM/tool-result usage.

## Notes

This is the measurement foundation for Sprint 3.
Live-path optimization continues in the active Sprint 3 stories.
