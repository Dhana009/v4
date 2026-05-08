# INT-GATE-001 Add live LLM policy gateway

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: LLM Runtime / Backend
Priority: P0

## Problem

Live agent.py still routes calls through a monolithic main_orchestrator loop.

The planned architecture requires a policy decision before each model call:
- is LLM needed
- purpose
- phase
- tools allowed
- context level
- schema
- fallback
- telemetry

## Source / architecture rule

- agent.py
- runtime/context_manager.py
- runtime/skill_policy.py
- runtime/deterministic_fast_path.py
- Complete LLM Mode Runtime Policy Spec

## Scope

Add a small policy gateway function/class used before LLM calls.

Gateway should return a decision object with:
- model_needed: bool
- purpose
- phase
- allowed_tools
- context_level
- schema_id
- budget
- deterministic_candidate_allowed
- fallback

## Out of scope

- Rewriting entire agent loop
- Multi-model routing
- Frontend changes

## Required tests

- gateway returns no-model decision for deterministic eligible input
- gateway returns purpose-specific decision for planning
- gateway restricts tool list by purpose
- gateway preserves backend confirmation requirement

## Acceptance criteria

- gateway exists and is covered by tests
- live model call path can consult gateway
- no behavior change unless explicitly wired by later stories

## Cost-aware verification plan

Run gateway unit tests only.
No E2E for this ticket.

## Evidence

To be filled during implementation.

## Notes

This is the live control-plane entry point.
