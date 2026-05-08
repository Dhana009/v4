# INT-LLM-003 Route step_plan_normalizer through LLMRuntimeController

Status: Backlog
Sprint: Sprint 3 Stretch
Type: Story
Owner: LLM Runtime
Priority: P2

## Source docs

- Complete LLM Mode Runtime Policy Spec
- PRD v2.3 LLM Runtime
- Complete LLM Mode P0 Scenario Spec

## Problem / Goal

Sprint 2 wired plan_diff_editor through LLMRuntimeController.

The next controller-routing target is step_plan_normalizer, but Sprint 3 core focus is token/call reduction first.

Goal:

Route focused Steps Mode planning through LLMRuntimeController using purpose=step_plan_normalizer.

## Scope

- Use LLMRuntimeController for step_plan_normalizer.
- Enforce purpose-specific tool policy.
- Enforce schema validation/retry.
- Emit telemetry with purpose, context level, skills, and token estimates.

## Out of scope

- Full journey_planner routing
- Multi-model routing
- Page validation recommender
- Full main loop rewrite

## Required tests

- Test focused steps planning uses purpose=step_plan_normalizer.
- Test invalid schema retries once and fails closed.
- Test tools exposed are restricted by purpose.
- Test telemetry records purpose and tokens.

## Acceptance criteria

- step_plan_normalizer is live-wired through controller.
- Existing E2E tests still pass.
- Token report records purpose correctly.

## Evidence

To be filled during implementation.

## Notes

Stretch only. Do not start until Sprint 3 core token/call optimization stories are stable.
