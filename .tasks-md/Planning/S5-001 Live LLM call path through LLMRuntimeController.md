# S5-001 Live LLM call path through LLMRuntimeController

Status: Planning
Sprint: Sprint 5
Type: Story
Owner: 
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, runtime/llm_runtime_controller.py, agent.py

## Problem / Goal

**Problem:** The live LLM call in agent.py bypasses LLMRuntimeController.call(). Purpose-specific policies (tool filtering, skill scoping, context compaction, token budgets, model routing, telemetry) exist but are never applied to actual model calls.

**Goal:** Wire planning LLM calls (step_plan_normalizer purpose) through LLMRuntimeController so policies are enforced at call time.

## Scope

- Route planning phase calls through LLMRuntimeController.call(purpose="step_plan_normalizer")
- Preserve current planning behavior and output
- Use fake model tests for verification (no paid LLM)
- Focus on planning purpose first; other purposes in future stories
- Ensure LLMPolicyGateway decision flows to controller invocation

Out of scope:
- Refactor agent.py broadly — only add wiring seams
- Implement all 14 purposes in one story
- Multi-model cheap/main routing (S5-008)
- Prompt pack implementation (S5-002)
- Context compaction (S5-005)

## Required unit tests

- `test_llm_runtime_controller_wiring.py`: LLMRuntimeController.call() receives correct purpose, phase, tools, context policy
- `test_llm_policy_gateway_to_controller.py`: LLMPolicyGateway decision → controller invocation
- `test_purpose_step_plan_normalizer_call.py`: step_plan_normalizer purpose call returns expected schema

## Required contract tests

- `test_controller_live_planning_call_contract.py`:
  - Planning call invokes controller with purpose="step_plan_normalizer"
  - Tools match step_plan_normalizer tool_policy
  - Output schema matches step_plan_normalizer output_schema
  - Telemetry fields recorded

## Required integration tests

- `test_planning_through_controller_fake_model.py`:
  - Fake model receives planning call with correct purpose
  - Plan output is valid JSON matching contract
  - No tool schema overhead vs fake input

## Fixture/page needs

None — purely wiring/fake-model focus.

## Paid E2E requirement

None. This story uses fake-model integration only.

## Acceptance criteria

- [ ] Live planning calls invoke LLMRuntimeController.call(purpose="step_plan_normalizer")
- [ ] LLMPolicyGateway.decide() output directly feeds controller call parameters
- [ ] Controller receives correct: phase, allowed_tools, context_level, schema_id, budget, fallback
- [ ] Telemetry includes purpose, model, call_id, skill_count, tools_exposed_count, context_level
- [ ] No ad-hoc bypass of controller for planning purpose
- [ ] All 5 E2E tests still pass (or E2E adapts to new wiring)
- [ ] Fake-model integration tests prove controller call path works

## Evidence

Will include:
- Unit test artifacts
- Contract test passing output
- Integration test fake-model call trace
- Modified agent.py diff (wiring only)
- Telemetry JSON sample showing purpose="step_plan_normalizer"

## Verification commands/results

```bash
pytest tests/test_llm_runtime_controller_wiring.py -v
pytest tests/test_llm_policy_gateway_to_controller.py -v
pytest tests/test_purpose_step_plan_normalizer_call.py -v
pytest tests/test_controller_live_planning_call_contract.py -v
pytest tests/test_planning_through_controller_fake_model.py -v
pytest tests/e2e -v --tb=short  # All E2E still pass
```

## Risk

- **Medium:** Agent.py wiring may break existing call flow if controller interface is not exact match
- **Low:** Fake model tests may not cover all real-LLM quirks (acceptable for fake-model-driven development)
- **Low:** Purpose="main_orchestrator" fallback may hide incomplete controller implementation

## Mitigation

- Contract tests verify controller→schema match exactly
- Fake-model suite comprehensive for planning output schema
- Fallback is explicit and logged
