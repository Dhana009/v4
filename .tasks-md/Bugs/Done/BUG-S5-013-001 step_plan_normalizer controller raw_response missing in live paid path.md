# BUG-S5-013-001 step_plan_normalizer controller raw_response missing in live paid path

Status: Done
Sprint: Sprint 5
Type: Bug
Severity: P0
Owner: Runtime / LLM Controller
Priority: P0
Started: 2026-05-11
Source docs: S5-013 paid E2E artifact, Sprint 5 runtime/token attribution contracts

## Root cause

The live `step_plan_normalizer` policy was still capped at `token_budget=2000`, but the paid artifact measured `estimated_total_input_tokens=2636`. The controller therefore hit its pre-call budget gate and returned a failure result with `raw_response=None`. `agent.py` surfaced that as `step_plan_normalizer controller did not return raw_response`.

The same artifact also exposed two telemetry fidelity gaps:
- `runtime/token_report.py` truncated digit-prefixed alphanumeric fields such as `timestamp` and `prefix_hash`.
- The live planning telemetry path did not emit `skill_levels`, so the token report could not preserve them.

## Fix

- Raised `step_plan_normalizer` token budget from `2000` to `3000` in `runtime/llm_runtime_controller.py`.
- Emitted `skill_levels` from the live planning telemetry path in `agent.py` using the already-loaded skill names.
- Fixed `runtime/token_report.py` parsing so digit-prefixed alphanumeric fields stay intact.
- Added token-report aggregation for `skill_levels`.

## Regression tests

- Added `tests/test_sprint5_paid_blocker_regression.py` for the paid-artifact budget gate, prefix-hash parsing, and skill-level aggregation.
- Extended `tests/test_planning_through_controller_fake_model.py` to require live planning telemetry to emit `skill_levels`.
- Extended `tests/test_llm_runtime_controller_contract.py` to cover the live tool-call shape with `content=None`.
- Extended `tests/test_token_report.py` and `tests/test_sprint5_llm_runtime_guardrails.py` to assert `skill_levels` is preserved in token reports.

## Token report fidelity

- `prefix_hash=657eb55c3207eee9` now survives parsing as the full 16-char string.
- `timestamp=2026-05-11T06:21:14.245Z` remains a string instead of truncating to `2026`.
- `skill_levels` is now emitted and preserved as a list in the token report when present.

## Tool schema investigation

- `tool_schema_tokens=584` is higher than the older baseline of `~410`, but this is expected from the current planning-safe tool set.
- `step_plan_normalizer` now exposes six planning-safe tools:
  - `send_to_overlay`
  - `browser_get_state`
  - `dom_extract`
  - `locator_find`
  - `locator_validate`
  - `ask_user`
- No narrow policy change was needed for this bug.

## Commands run

- `python -m py_compile agent.py runtime/llm_runtime_controller.py runtime/telemetry.py runtime/token_report.py tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_telemetry_breakdown.py tests/test_token_report.py tests/test_sprint5_paid_blocker_regression.py`
- `python -m pytest tests/test_sprint5_paid_blocker_regression.py -q`
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py -q`
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q`
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_fake_llm_factory.py -q`

## Results

- `py_compile`: passed
- paid-blocker regression suite: 3 passed
- controller/planning contract suite: 33 passed
- telemetry/token report suite: 46 passed
- Sprint 5 guardrails: 34 passed
- broader cheap runtime safety suite: 54 passed

## Changed files

- `agent.py`
- `runtime/llm_runtime_controller.py`
- `runtime/token_report.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_planning_through_controller_fake_model.py`
- `tests/test_sprint5_llm_runtime_guardrails.py`
- `tests/test_token_report.py`
- `tests/test_sprint5_paid_blocker_regression.py`
- `.tasks-md/Bugs/Done/BUG-S5-013-001 step_plan_normalizer controller raw_response missing in live paid path.md`

## Commit

- pending
