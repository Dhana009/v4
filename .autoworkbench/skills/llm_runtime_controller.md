# Skill: LLM Runtime Controller

## Purpose
Prevent uncontrolled LLM usage, token explosion, broad tool exposure, and one giant main_orchestrator loop.

## When to use
Use when touching LLM calls, prompts, model_router, context_manager, skill loading, tool filtering, recovery LLM, plan generation, locator LLM, or telemetry.

## Source of truth
- LLM Runtime Policy Spec
- PRD LLM runtime guidance
- Token/log failure evidence from previous runs

## Non-negotiable rules
1. No ad-hoc direct LLM calls.
2. Every LLM call must have an explicit purpose.
3. LLM Runtime Controller selects policy before call.
4. Deterministic backend path must be tried first when available.
5. Each call declares model, persona, skills, context level, tools, schema, token budget, retry policy, validator.
6. LLM can request context; backend approves or denies.
7. Backend validates every LLM output.
8. Full DOM, full history, and all skills are never default.
9. Tool exposure must be purpose-specific.
10. Human feedback is preferred over guessing when ambiguity is real.
11. LLM never owns execution, recording, or completion.

## Required implementation behavior
Implement or preserve:
- purpose taxonomy
- model routing policy
- context sufficiency gates
- skill loading levels
- tool policy matrix
- schema validation
- pre-call and post-call quality gates
- memory retrieval policy
- token telemetry
- trace events for every LLM call

## Required tests
Add/update tests for:
- purpose selection
- tool filtering by purpose/phase
- context level selection
- skill loading by purpose
- schema retry/fail-closed
- token budget enforcement/telemetry
- context request approval/denial
- no direct main_orchestrator fallback

## Verification commands
```bash
python -m pytest tests/test_context_manager.py tests/test_tool_registry.py -q
```
Add focused tests as modules are created.

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- implementation keeps one all-purpose LLM path
- tools are exposed broadly without policy
- skills load by broad phase only
- context builder sends full history/DOM by default
- LLM output is consumed without schema/backend validation

## Reporting format
Report:
1. LLM purposes affected
2. Policy implemented/changed
3. Context/skill/tool behavior
4. Token telemetry impact
5. Tests/results
6. Risks
