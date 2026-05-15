# INT-GATE-001 Add live LLM policy gateway

Status: Done
Sprint: Sprint 3
Type: Story
Owner: LLM Runtime / Backend
Priority: P0
Started: 2026-05-08 20:00 IST

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

- `python -m py_compile agent.py runtime/llm_policy_gateway.py tests/test_llm_policy_gateway.py` -> passed
- `python -m pytest tests/test_llm_policy_gateway.py -q` -> 5 passed

## Implementation summary

- added `runtime/llm_policy_gateway.py` with a typed live policy-gateway decision object
- gateway can recommend deterministic no-model planning, purpose-specific planning, correction, execution, and recovery decisions
- `agent.py` now instantiates the gateway and consults it before the main LLM call without changing routing behavior yet

## Notes

This is the live control-plane entry point.
