# BUG-S5-013-003 model_class main passed as provider model name

Status: Done
Sprint: Sprint 5
Owner:
Source docs: S5-013 paid retry artifact, BUG-S5-013-001, BUG-S5-013-002, Sprint 5 controller raw-response contract, Sprint 5 model routing contract

## Problem

The third controlled paid retry reached the live LLM, but the planning call still failed before plan review or clarification. The failure is no longer the generic missing-`raw_response` mask from the earlier blocker. The backend now exposed the real provider/model routing problem:

- `The model \`main\` does not exist or you do not have access to it.`
- `NotFoundError`
- `Error code: 404`

The internal `model_class` value `main` was being used as if it were the provider model name. That is wrong. `model_class` is routing metadata and must be resolved to an actual provider model string before the OpenAI call. In this checkout the configured actual model is `gpt-4o-mini`.

## Paid artifact evidence

- Flow: `tests/e2e/test_llm_required_ambiguous_action_flow.py`
- Retry artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-134142-28864/`
- Pytest failure: `TimeoutError: Timed out waiting for plan review or clarification`
- Backend stage evidence:
  - `stage=llm_response_seen`
  - `llm_triggered=true`
  - `error_type=RuntimeError`
  - `error_message` includes `step_plan_normalizer controller did not return raw_response: MODEL_CALL_FAILED | Error code: 404 ... model_not_found`
- Backend tail evidence:
  - `purpose=step_plan_normalizer`
  - `model=gpt-4o-mini`
  - `prompt_pack_id=step_plan_normalizer.v1`
  - `prefix_hash=657eb55c3207eee9`
  - `skills_loaded=core,actions,download`
  - `skill_levels=skill_summary,skill_summary,skill_summary`
  - `model_class=main`
  - `error_message` still references provider failure for model `main`
  - `tool_schema_tokens=584`
- Token report evidence:
  - `total_estimated_input_tokens=2636`
  - `total_output_tokens=0`
  - `system=840`
  - `skill=1699`
  - `tool_schema=584`
  - `history=238`
  - `prompt_pack_ids=["step_plan_normalizer.v1"]`
  - `prefix_hash=657eb55c3207eee9`
  - `skill_levels=["skill_summary"]`
  - `model_classes=["main"]`
  - `records[0]["model"]="gpt-4o-mini"`
  - `records[0]["model_class"]="main"`

## Root cause

The live provider path was resolving the internal `model_class` `main` into the provider request instead of mapping it to the configured provider model. The controller needed a small explicit resolution seam so internal model classes never leak directly to the provider.

## Fix

- Added `resolve_model_name(...)` in `runtime/model_router.py`.
- `ModelRouter.call()` now resolves internal model classes before calling the provider.
- `LLMRuntimeController` now resolves the provider model from the policy or explicit override before calling the client.
- Explicit provider overrides like `dummy-model` still pass through unchanged when they are not internal model classes.
- Internal aliases continue to be recorded separately in telemetry as `model_class`.

## Model resolution behavior

- `main` resolves to `gpt-4o-mini` in this checkout unless a configured main model is provided.
- `cheap` falls back to the configured main model or the default provider model.
- `debug` falls back to the configured main model or the default provider model.
- Direct provider model overrides are preserved when they are not internal aliases.
- Unknown internal model classes fail closed instead of being sent to the provider as-is.

## Scope

- Add a small `resolve_model_name(...)` seam in `runtime/model_router.py`.
- Make the controller resolve the provider model before calling OpenAI.
- Preserve the controller raw-response contract and failure diagnostics.
- Keep prompt-pack and telemetry attribution intact on both success and failure paths.
- Keep `model_class` telemetry separate from the provider `model` string.

## Out of scope

- Paid reruns during this ticket
- Full S5-008 multi-model routing
- Prompt pack content changes
- Frontend changes
- Broad runtime refactors

## Required tests

- `tests/test_model_router.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_token_report.py`
- `tests/test_sprint5_paid_retry_blocker_regression.py`
- `tests/test_sprint5_paid_blocker_regression.py`

## Acceptance criteria

- `model_class="main"` resolves to `gpt-4o-mini` or an explicitly configured main model before the provider call.
- `cheap` and `debug` fallback explicitly instead of leaking internal labels to the provider.
- Unknown model classes do not reach the provider as-is.
- Controller telemetry keeps `model_class` separate from the provider `model`.
- The ambiguous planning flow can be retried safely after the routing fix is verified cheaply.

## Evidence

- The retry reached the model once and failed with a provider 404, not a generic local-only startup issue.
- The backend telemetry was more specific than the earlier blocker, which confirmed BUG-S5-013-002 fixed the masking layer.
- The current blocker was model-class leakage into provider routing, and the fix now resolves it cheaply.

## Verification commands/results

- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py -q` -> passed
- `python -m pytest tests/test_sprint5_paid_blocker_regression.py -q` -> passed
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q` -> passed
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_telemetry_breakdown.py tests/test_token_report.py -q` -> passed
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q` -> failed after one live LLM call with `TimeoutError` and provider `model_not_found`
- `python -m pytest tests/test_model_router.py -q` -> 8 passed
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py -q` -> 34 passed
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q` -> 47 passed
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q` -> 34 passed
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_fake_llm_factory.py tests/test_backend_event_sequences.py tests/test_recording_codegen_truth_contract.py -q` -> 62 passed
