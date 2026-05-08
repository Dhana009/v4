# BUG-RUNTIME-004 execution_driver exposed zero tools in executing phase

Status: Done
Sprint: Sprint 3
Type: Bug
Severity: P0
Owner: Runtime / Tool Policy
Priority: P0
Started: 2026-05-08 21:35 IST

## Source / Contract violated

- Confirmed corrected plans must continue into backend-truth execution after user confirmation.
- `execution_driver` cannot be the live execution purpose while exposing zero execution tools.

## Expected

After a corrected plan is confirmed, the live execution path should expose only the execution tools needed to drive the confirmed child operations.

## Actual

`correction_assert_then_click_flow` reached corrected `plan_ready` and confirmation, then stalled in `PLAN REVIEW` because `execution_driver` had `allowed_tools=0` in `executing`.

Artifact:

`test-results/autoworkbench-e2e/correction_assert_then_click_flow-20260508-205107-61213`

## Root cause

`runtime/llm_runtime_controller.py` defined `execution_driver` with planning tools only. `_purpose_policy()` did not receive an `executing_tools` set for that purpose, so the live gateway routed execution into a zero-tool model call.

## Fix plan

- Extend `_purpose_policy()` to accept `executing_tools`.
- Give `execution_driver` the narrow execution set: `action_assert`, `action_click`, `action_fill`.
- Update gateway/planning contract tests to reflect the live execution contract.

## Verification

- Focused tests:
  - `python -m pytest tests/test_llm_policy_gateway.py tests/test_llm_planning_contracts.py tests/test_deterministic_fast_path.py tests/test_plan_correction.py -q`
- Paid E2E:
  - `python -m pytest tests/e2e/test_correction_assert_then_click_flow.py -q -s`
- Result:
  - corrected confirmed plans now leave `PLAN REVIEW` and execute normally
  - `correction_assert_then_click_flow` passed after the fix
