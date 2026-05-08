# INT-E2E-002 Token-budget regression checks

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: E2E / Evidence
Priority: P1

## Source docs

- PRD v2.3 Build Roadmap and Acceptance
- Complete LLM Mode Runtime Policy Spec
- Sprint 3 cost optimization plan

## Problem / Goal

E2E tests should not silently explode token usage.

Goal:

Add token/call budget evidence to regression runs.

## Scope

E2E artifact/report should include:

- LLM calls per test
- estimated input tokens per test
- output tokens when available
- largest prompt
- top token source
- skills loaded
- context level
- model/purpose breakdown

Initial thresholds can be warning-only until stable.

## Out of scope

- Hard CI failure thresholds for every test
- OpenAI billing dashboard integration
- Full trace UI redesign

## Required tests

- Test E2E artifact includes token/call report.
- Test report includes calls per test and total estimated tokens.
- Test warning is produced when threshold is exceeded.
- Test report generation does not fail when token data is partially missing.

## Acceptance criteria

- E2E report includes token usage summary.
- Token regressions are visible locally.
- Existing 5 E2E tests still pass.
- Sprint 3 before/after token comparison can be produced.

## Evidence

To be filled during implementation.

## Notes

This makes token optimization measurable in future sprints.
