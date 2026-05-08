# INT-LLM-004 Add LLM-required E2E acceptance coverage

Status: Done
Sprint: Sprint 3
Type: Story
Owner: LLM Runtime / E2E
Priority: P0
Started: 2026-05-08 21:40 IST
Completed: 2026-05-08 21:56 IST

## Problem

Sprint 3 optimized deterministic flows to 0 LLM calls, but we still need acceptance evidence that the LLM path works for flows that require reasoning.

Current deterministic E2E coverage proves:
- simple picker-backed click/assert flows avoid LLM
- backend fast path works
- token cost is zero for deterministic flows

Missing coverage:
- ambiguous or broad user intent should invoke the LLM path
- policy gateway should choose a specific purpose
- token-report.json should record LLM calls
- deterministic fast path should not over-apply

## Source / architecture rule

Complete LLM Mode must use deterministic backend/DOM paths when safe, but must use LLM reasoning when intent is ambiguous, broad, or requires planning/recommendation.

## Scope

Add 1–2 E2E tests that naturally trigger the LLM path through a normal page URL and user instruction.

The test must not inject internal backend plan structures.

## Required tests

At minimum:

1. Ambiguous action flow:
   - page contains ambiguous duplicate targets
   - user asks a natural ambiguous instruction
   - deterministic fast path must not fire
   - LLM must be called
   - system must ask clarification or propose a safe plan, not execute blindly

2. Broad page reasoning flow:
   - user asks the agent to inspect/recommend validations for a page/section
   - LLM must be called with a specific purpose
   - page intelligence/compact context should be used
   - no browser-changing action before confirmation

## Acceptance criteria

- At least one new E2E test proves LLM call count > 0.
- token-report.json records the LLM call(s).
- purpose is not incorrectly reported as deterministic/fast path.
- if a specific purpose is expected, telemetry records it.
- deterministic fast path does not trigger for ambiguous/broad instructions.
- no browser action occurs before confirmation.
- existing 5 deterministic E2E tests still pass.
- non-E2E tests pass.

## Cost-aware verification plan

Use focused E2E only:
- run the new ambiguous/broad LLM test once during development
- run existing 5 deterministic E2E once at final acceptance only

## Evidence

- New LLM-required E2E test:
  - `tests/e2e/test_llm_required_ambiguous_action_flow.py`
- New fixture:
  - `tests/e2e/fixtures/test_app/ambiguous-actions.html`
- Latest acceptance artifact:
  - `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260508-212504-78786/token-report.json`

## Verification

- py_compile:
  - `python -m py_compile tests/e2e/test_llm_required_ambiguous_action_flow.py`
  - `python -m py_compile tests/e2e/harness.py runtime/token_report.py`
- targeted LLM E2E:
  - `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q -s`
  - result: `1 passed`
- non-E2E regression:
  - `python -m pytest tests/ --ignore=tests/e2e -q`
  - result: `509 passed`
- final acceptance E2E:
  - `python -m pytest tests/e2e/test_basic_click_flow.py tests/e2e/test_exact_text_assertion_flow.py tests/e2e/test_visible_assertion_flow.py tests/e2e/test_correction_assert_then_click_flow.py tests/e2e/test_mvp_001_lifecycle_smoke.py tests/e2e/test_llm_required_ambiguous_action_flow.py -q -s`
  - result: `6 passed`

## Result

Confirmed:
- deterministic flows still use `0` LLM calls
- ambiguous natural-language flow invokes the LLM
- `token-report.json` records LLM usage
- telemetry records `purpose=step_plan_normalizer`
- deterministic fast path does not qualify
- no execution contract or browser action occurs before confirmation

## Notes

- Sprint 3 acceptance scope is satisfied with one natural-language ambiguous-action E2E.
- Broad page recommendation coverage can move to Sprint 4 if additional LLM-mode acceptance breadth is needed.
