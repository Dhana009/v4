# S5-001 Live LLM call path through LLMRuntimeController

Status: Planning
Sprint: Sprint 5
Type: Story
Owner: 
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, runtime/llm_runtime_controller.py, agent.py

## Problem / Goal

**Problem:** The live LLM call in agent.py bypasses LLMRuntimeController.call() for the main planning loop. Purpose-specific policies (tool filtering, skill scoping, context compaction, token budgets, model routing, telemetry) exist but are never applied to actual planning calls.

**Goal:** Wire step_plan_normalizer planning calls through LLMRuntimeController so policies are enforced at call time.

**Architecture note (from SPRINT-005-ARCH-DESIGN):**
- plan_diff_editor is ALREADY wired through `_plan_diff_editor_controller.call()` — this is the reference implementation.
- S5-001 scope is step_plan_normalizer ONLY — not all 14 purposes.
- Use a shared `_llm_purpose_controller` pattern (not one controller per purpose) to avoid proliferation.
- Cluster 1 (S5-012 + S5-007) must be complete and green before S5-001 starts.
- S5-001 is Cluster 2.

## Scope

- Wire step_plan_normalizer planning calls through a shared `_llm_purpose_controller.call(purpose="step_plan_normalizer")`
- Follow the `_plan_diff_editor_controller` pattern already in agent.py as reference
- Preserve current planning behavior and output schema
- Use FakeLLMClient from tests/fake_llm_factory.py for verification (no paid LLM)
- Telemetry must include purpose, skills_loaded, model_class, context_bucket from S5-007 fields
- recovery_diagnoser may be wired in the same story if low risk, but step_plan_normalizer is the acceptance gate

Out of scope:
- Wiring all 14 purposes — step_plan_normalizer only
- Broad agent.py refactor — wiring seam only
- Multi-model cheap/main routing (S5-008)
- Prompt pack implementation (S5-002)
- Context compaction changes (S5-005)
- plan_diff_editor (already wired — reference only)

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
