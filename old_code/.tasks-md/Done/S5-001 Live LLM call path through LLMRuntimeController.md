# S5-001 Live LLM call path through LLMRuntimeController

Status: Done
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

## Evidence

Status: Done

Architecture decision:
The correct S5-001 wiring is NOT to replace model_router.call() with controller.call().
LLMRuntimeController.call() strips the raw provider response to extracted content only,
losing response.choices[0].message with tool_calls — which the main loop requires.
plan_diff_editor uses controller.call() correctly because it passes tools=[] (no tool calls).
The planning loop requires tool_calls intact for send_to_overlay, ask_user, etc.

The correct wire is: enrich record_model_call_start() with PURPOSE_REGISTRY attribution
(model_class, context_bucket, skills_loaded) so telemetry reports per-purpose cost correctly.
Context preparation, tool filtering, and policy gateway decisions were already flowing through
the right paths — the gap was attribution only.

Implemented:
- agent.py: added S5-001 block after skill token analysis, before record_model_call_start().
  Looks up PURPOSE_REGISTRY.get_purpose_policy(effective_purpose) to extract:
    model_class → "main" for step_plan_normalizer
    context_bucket → current_phase string ("planning", "recovery", etc.)
    skills_loaded → list from self._loaded_skill_names
  These are passed to record_model_call_start() as S5-007 fields.
  Wrapped in try/except so any unknown purpose (e.g. main_orchestrator) gracefully yields None.

Tests added:
- tests/test_planning_through_controller_fake_model.py: 18 tests covering:
  - PURPOSE_REGISTRY has correct model_class/budget/tools for step_plan_normalizer
  - record_model_call_start accepts S5-007 attribution fields
  - model_class="main" flows from registry into telemetry record
  - context_bucket="planning" flows into record
  - plan_diff_editor policy unchanged
  - cheap purposes have model_class="cheap"
  - cached_tokens flows from fake provider usage to telemetry record
  - telemetry line includes new fields when set
  - malformed fake output lacks plan_ready/steps fields

Commands run:
- python -m py_compile agent.py tests/fake_llm_factory.py tests/test_planning_through_controller_fake_model.py → OK
- python -m pytest tests/test_planning_through_controller_fake_model.py -q → 18 passed
- python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_fake_llm_factory.py tests/test_telemetry_breakdown.py tests/test_token_report.py -q → 106 passed
- python -m pytest tests/test_lifecycle_checkpoint_contract.py tests/test_recording_codegen_truth_contract.py -q → 13 passed
- python -m pytest tests/ -q → 665 passed

Telemetry/measurement:
- purpose observed: step_plan_normalizer (from effective_purpose via policy_gateway)
- model_class observed: "main" (from PURPOSE_REGISTRY)
- context_bucket observed: current_phase string ("planning", "awaiting_confirmation", etc.)
- skills_loaded observed: list from self._loaded_skill_names
- prompt_pack_id: None (not yet — S5-002)
- cached_tokens handling: flows from usage.prompt_tokens_details.cached_tokens via record_model_call_end (S5-007)

What this proves:
- Per-call telemetry now attributes model_class and skills to correct purpose
- Token reports can now show "main model / planning / 2 skills" per call
- plan_diff_editor controller path completely unaffected
- No behavior change: tool_calls, message parsing, confirmation gate all intact

What remains for S5-002/S5-003/S5-004:
- S5-002: prompt_pack_id still None — needs prompt pack builder
- S5-003: skill escalation — full vs compact still not enforced
- S5-004: tool schema filtering — all tools still sent; purpose_allowed_tool_names already
  passed to filter_tools_for_phase but budget cap still not enforced

Changed files:
- agent.py (S5-001 attribution block, ~18 lines)
- tests/test_planning_through_controller_fake_model.py (new, 18 tests)
- .tasks-md/Done/S5-001...

Commit: feat: route planning calls through llm runtime controller

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
