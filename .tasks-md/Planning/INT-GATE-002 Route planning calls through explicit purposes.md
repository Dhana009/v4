# INT-GATE-002 Route planning calls through explicit purposes

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: LLM Runtime
Priority: P0

## Problem

Telemetry shows all calls are purpose=main_orchestrator.

This prevents purpose-specific tool, skill, schema, and context policies from taking effect.

## Source / architecture rule

- agent.py
- runtime/telemetry.py
- runtime/context_manager.py
- runtime/skill_policy.py
- Complete LLM Mode Runtime Policy Spec
- Sprint 3 token diagnosis report

## Scope

Route planning-related calls through explicit purposes where safe:
- simple planning / step normalization: step_plan_normalizer or equivalent
- plan correction: plan_diff_editor
- locator specialist only when deterministic locator cannot resolve
- fallback main_orchestrator only when no narrower purpose applies

## Out of scope

- Full main loop rewrite
- Multi-model routing
- Frontend changes

## Required tests

- planning call records explicit purpose, not main_orchestrator, when mapped
- fallback main_orchestrator still exists for unsupported broad cases
- telemetry records purpose
- existing plan/correction flows still pass focused tests

## Acceptance criteria

- at least one live planning path no longer records main_orchestrator
- no quality regression
- no pre-confirm execution

## Cost-aware verification plan

Run focused LLM/controller/agent tests.
Run one E2E only if needed to validate live telemetry.
Full 5 E2E only at final acceptance.

## Evidence

To be filled during implementation.

## Notes

This is the first live step away from generic orchestration.
