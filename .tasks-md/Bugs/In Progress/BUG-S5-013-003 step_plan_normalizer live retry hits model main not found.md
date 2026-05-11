# BUG-S5-013-003 step_plan_normalizer live retry hits model main not found

Status: In Progress
Sprint: Sprint 5
Owner:
Source docs: S5-013 paid retry artifact, BUG-S5-013-001, BUG-S5-013-002, Sprint 5 controller raw-response contract

## Problem

The third controlled paid retry reached the live LLM, but the planning call still failed before plan review or clarification. The failure is no longer the generic missing-`raw_response` mask from the earlier blocker. The backend now exposes a provider/model availability error:

- `The model \`main\` does not exist or you do not have access to it.`
- `NotFoundError`
- `Error code: 404`

Because the provider request fails in the live path, the ambiguous planning flow times out waiting for plan review or clarification and cannot complete S5-013 acceptance.

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
  - `prompt_pack_id=step_plan_normalizer.v1`
  - `prefix_hash=657eb55c3207eee9`
  - `skills_loaded=core,actions,download`
  - `skill_levels=skill_summary,skill_summary,skill_summary`
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

## Root cause

The live provider path is still resolving to a `main` model identity that the provider rejects with `model_not_found`. That means the remaining blocker is no longer the raw-response envelope itself; it is the live model selection / provider routing for the planning call.

## Scope

- Verify and correct the live `step_plan_normalizer` model selection or provider routing.
- Preserve the controller raw-response contract and failure diagnostics.
- Keep prompt-pack and telemetry attribution intact on both success and failure paths.

## Out of scope

- Paid reruns during this ticket
- Prompt pack content changes
- Tool policy changes
- Broad runtime refactors
- Frontend changes

## Required tests

- `tests/test_sprint5_paid_retry_blocker_regression.py`
- `tests/test_sprint5_paid_blocker_regression.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_planning_through_controller_fake_model.py`
- A follow-up live-smoke or provider-routing contract test after the model selection fix

## Acceptance criteria

- The live planning path no longer fails with `model_not_found` for `main`.
- The ambiguous planning flow reaches plan review or clarification.
- The controller still preserves `raw_response`, `raw_message`, `content`, and `tool_calls`.
- Prompt-pack attribution remains present in telemetry and token reports.
- S5-013 remains blocked until a successful controlled retry is approved.

## Evidence

- The retry reached the model once and failed with a provider 404, not a generic local-only startup issue.
- The backend telemetry is now more specific than the earlier blocker, which confirms BUG-S5-013-002 fixed the masking layer.
- The live provider/model routing still needs correction before another paid retry.

## Verification commands/results

- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py -q` -> passed
- `python -m pytest tests/test_sprint5_paid_blocker_regression.py -q` -> passed
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q` -> passed
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_telemetry_breakdown.py tests/test_token_report.py -q` -> passed
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q` -> failed after one live LLM call with `TimeoutError` and provider `model_not_found`
