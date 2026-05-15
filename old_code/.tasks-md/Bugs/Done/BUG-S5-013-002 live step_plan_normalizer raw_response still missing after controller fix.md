# BUG-S5-013-002 live step_plan_normalizer raw_response still missing after controller fix

Status: Done
Sprint: Sprint 5
Owner:
Source docs: S5-013 paid retry artifact, BUG-S5-013-001, Sprint 5 controller raw-response contract

## Problem

BUG-S5-013-001 raised the planning token budget and added fake coverage, but the live ambiguous-planning flow still failed after the real LLM call. The backend still logged:

- `step_plan_normalizer controller did not return raw_response`
- the retry timed out waiting for plan review or clarification
- the failed retry token report dropped `prompt_pack_id` and `prefix_hash`

The controller raw-response path was still not preserving the real live failure details.

## Paid artifact evidence

- Flow: `tests/e2e/test_llm_required_ambiguous_action_flow.py`
- Retry artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-125206-72380/`
- Failure: timeout waiting for plan review or clarification
- Backend telemetry: `step_plan_normalizer controller did not return raw_response`
- Retry token data:
  - input tokens: 2582 vs 4442 baseline
  - system: 1748 vs ~3496 baseline
  - skill: 1699 vs ~3398 baseline
  - tool_schema: 584 vs ~410 baseline
  - history: 238 vs ~495 baseline
  - prompt_pack_id: absent from token-report.json
  - prefix_hash: absent from token-report.json
  - skills_loaded: core,actions,download
  - skill_levels: skill_summary
  - purpose: step_plan_normalizer
  - model_class: main

## Root cause

- `call_with_raw_response(...)` allowed provider-call exceptions and `None` responses to escape without a normalized failure envelope.
- The agent adapter then flattened the controller failure into a generic `step_plan_normalizer controller did not return raw_response` error.
- Because the controller never returned the prompt-pack metadata on that failure path, `prompt_pack_id` and `prefix_hash` were missing from the failed telemetry and token report.

## Fix

- `call_with_raw_response(...)` now normalizes model-call exceptions into a failure envelope with:
  - `raw_response = None`
  - `raw_message = None`
  - `content = None`
  - `tool_calls = []`
  - `error_code = MODEL_CALL_FAILED`
  - `message` and `errors` preserving the provider exception detail
  - prompt-pack metadata retained on the failure result
- `call_with_raw_response(...)` now also normalizes a `None` model response into a failure envelope.
- `agent.py` now reports the controller's error detail when `raw_response` is missing instead of flattening everything to a generic message.

## Scope

- Reproduce the live failure cheaply with fake controller/client behavior.
- Preserve failure metadata on the controller return path.
- Surface the real controller error detail in the agent adapter instead of collapsing everything into a generic missing-raw-response error.
- Keep prompt-pack metadata visible on failed telemetry and token reports.

## Out of scope

- Paid E2E reruns
- Live LLM debugging
- Prompt pack content changes
- Tool policy changes
- Broad refactors

## Required tests

- `tests/test_sprint5_paid_retry_blocker_regression.py`

## Acceptance criteria

- The controller returns a failure envelope instead of throwing when the model client raises or returns `None`.
- The failure envelope preserves `prompt_pack_id`, `prefix_hash`, `skills_loaded`, and `skill_levels`.
- The agent adapter reports the controller error detail when `raw_response` is missing.
- Failed telemetry lines keep prompt-pack attribution so token-report parsing sees it.

## Evidence

- The new regression suite reproduces the blocker cheaply and passes after the fix.

## Verification commands/results

- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py -q` -> 4 passed
- `python -m py_compile agent.py runtime/llm_runtime_controller.py runtime/telemetry.py runtime/token_report.py tests/test_sprint5_paid_retry_blocker_regression.py tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_token_report.py tests/test_telemetry_breakdown.py`
- `python -m pytest tests/test_sprint5_paid_blocker_regression.py -q` -> 3 passed
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py -q` -> 33 passed
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q` -> 46 passed
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q` -> 34 passed
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_fake_llm_factory.py tests/test_backend_event_sequences.py tests/test_recording_codegen_truth_contract.py -q` -> 67 passed
