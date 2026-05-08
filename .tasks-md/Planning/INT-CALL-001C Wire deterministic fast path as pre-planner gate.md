# INT-CALL-001C Wire deterministic fast path as pre-planner gate

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: Backend / LLM Runtime
Priority: P0

## Problem

No [FAST_PATH] lines appeared in E2E. Simple flows still enter main_orchestrator planning loop.

## Source / architecture rule

- agent.py
- runtime/deterministic_fast_path.py
- runtime/telemetry.py
- Complete LLM Mode Runtime Policy Spec
- Sprint 3 token diagnosis report

## Scope

Wire _try_deterministic_fast_path() before the main LLM loop.

Fast path applies only when:
- single-step picked-element flow
- locator validates exactly one visible/compatible element
- action is click, fill, assert_visible, or assert_text
- no compound/multi-step intent

If qualifies:
- emit plan_ready with backend-compatible plan shape
- wait for normal confirmation
- execute through existing backend path after confirmation
- emit telemetry showing model_called=false / llm_calls=0 for planning

If correction/rejection/ambiguity occurs:
- fall back to normal LLM path

## Out of scope

- Executing before confirmation
- Skipping backend validation
- Handling broad multi-step journeys

## Required tests

- fast path emits plan_ready without model call
- fast path still requires confirmation
- browser action does not happen before confirmation
- rejected/corrected plan falls back safely
- basic click flow emits [FAST_PATH] marker

## Acceptance criteria

- basic_click call count drops materially
- [FAST_PATH] appears in basic_click artifacts
- all 5 E2E pass at final acceptance

## Cost-aware verification plan

Run unit tests first.
Then run only basic_click E2E once to validate fast path.
Do not run all 5 E2E until final acceptance.

## Evidence

To be filled during implementation.

## Notes

This is the call-count reduction lever, not only a prompt-size change.
