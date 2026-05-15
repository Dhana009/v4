# INT-LLM-003 Route step_plan_normalizer through LLMRuntimeController

Status: Done
Sprint: Sprint 5 (S5-001)
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

Superseded and completed by S5-001 (Sprint 5). `agent.py:3840 _call_step_plan_normalizer_controller` routes through `LLMRuntimeController` with `purpose=step_plan_normalizer`. Tool policy, schema validation, and telemetry attribution all wired. Tests: `test_planning_through_controller_fake_model.py`, `test_llm_runtime_controller_contract.py`, `test_tool_schema_filter.py`. Paid E2E artifact confirms live routing (`[MODEL_ROUTER] purpose=step_plan_normalizer`). HEAD at closure: `17c86ef`.

## Notes

Originally a Sprint 3 stretch backlog item. Promoted and fully implemented in Sprint 5 as S5-001.
