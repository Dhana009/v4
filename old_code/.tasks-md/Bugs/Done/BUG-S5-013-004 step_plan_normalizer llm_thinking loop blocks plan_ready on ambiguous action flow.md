Status: Done
Sprint: Sprint 5
Owner: AutoWorkbench

Problem:
- The live `step_plan_normalizer` planning path could repeat `llm_thinking` tool calls without converging to `plan_ready` or clarification.
- The harness timed out while waiting for plan review or clarification, and token usage exploded during the loop.

Source/evidence:
- Paid retry artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-141048-68814/`
- Backend logs showed repeated `send_to_overlay({"message_type":"llm_thinking"})` tool calls.
- No `plan_ready` or clarification was reached before timeout.
- Input tokens reached `60326` versus the `4442` baseline.

Root cause hypothesis:
- Sprint 5 had backend guardrails for raw-response preservation, model routing, prompt packs, and context compaction.
- It did not yet have a backend-owned convergence guard for repeated non-terminal planning turns.

Root cause:
- `step_plan_normalizer` lacked a no-progress guard for repeated non-terminal planning turns.
- Valid-but-non-terminal `llm_thinking` / planning tool-call turns could loop until timeout and history growth.

Scope:
- Add a pure backend planning-loop guard.
- Integrate it into the `step_plan_normalizer` path before assistant tool calls are appended or executed.
- Add cheap deterministic tests that reproduce the repeated-thinking failure.

Out of scope:
- Paid E2E.
- Live LLM app runs.
- Prompt rewrite as the primary fix.
- Frontend changes.
- Broad refactors of the runtime or controller architecture.

Fix:
- Added `runtime/planning_loop_guard.py` with a pure planning-loop inspection and no-progress decision helper.
- Integrated the guard in `agent.py` before assistant tool calls are appended or executed for `step_plan_normalizer`.
- The backend now rejects repeated non-terminal planning turns with `runtime_rejected` and `PLANNING_NO_PROGRESS` instead of looping indefinitely.

Loop guard:
- `max_consecutive_thinking_only_turns = 2`
- `max_planning_turns_without_terminal_output = 3`
- `llm_thinking` counts toward the thinking-only counter.
- `plan_ready`, `ask_user`, clarification, and explicit failure-style outputs reset progress.
- Browser/execution-style tool calls do not count as terminal planning progress.

Required unit tests:
- `tests/test_planning_loop_guard.py`
- `tests/test_backend_event_sequences.py`
- `tests/test_recording_codegen_truth_contract.py`

Required contract tests:
- `tests/test_planning_through_controller_fake_model.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_context_manager.py`
- `tests/test_token_report.py`
- `tests/test_telemetry_breakdown.py`

Required integration tests:
- `tests/test_sprint5_paid_retry_blocker_regression.py`
- `tests/test_sprint5_paid_blocker_regression.py`
- `tests/test_prompt_cache_strategy.py`
- `tests/test_sprint5_llm_runtime_guardrails.py`
- `tests/test_prompt_pack_builder.py`
- `tests/test_prompt_pack_safety_rules.py`
- `tests/test_correction_context.py`
- `tests/test_recovery_context.py`
- `tests/test_skill_selector.py`
- `tests/test_skill_escalation_contract.py`
- `tests/test_tool_schema_filter.py`
- `tests/test_tool_policy_contract.py`
- `tests/test_fake_llm_factory.py`

Acceptance criteria:
- Repeated thinking-only planning turns stop before the harness timeout.
- The backend emits a typed `runtime_rejected` event with `PLANNING_NO_PROGRESS`.
- No `plan_ready`, `step_recorded`, `code_update`, or `run_completed` is emitted on the no-progress path.
- The guard is cheap, deterministic, and backend-owned.
- The fix does not change prompt text or require paid validation.

Regression tests:
- `tests/test_planning_loop_guard.py`
- `tests/test_planning_through_controller_fake_model.py`
- `tests/test_sprint5_paid_retry_blocker_regression.py`
- `tests/test_sprint5_paid_blocker_regression.py`
- `tests/test_prompt_cache_strategy.py`
- `tests/test_sprint5_llm_runtime_guardrails.py`
- `tests/test_context_manager.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_telemetry_breakdown.py`
- `tests/test_token_report.py`
- `tests/test_prompt_pack_builder.py`
- `tests/test_prompt_pack_safety_rules.py`
- `tests/test_correction_context.py`
- `tests/test_recovery_context.py`
- `tests/test_skill_selector.py`
- `tests/test_skill_escalation_contract.py`
- `tests/test_tool_schema_filter.py`
- `tests/test_tool_policy_contract.py`
- `tests/test_fake_llm_factory.py`
- `tests/test_backend_event_sequences.py`
- `tests/test_recording_codegen_truth_contract.py`

Verification commands/results:
- `python -m py_compile agent.py runtime/planning_loop_guard.py tests/test_planning_loop_guard.py tests/test_planning_through_controller_fake_model.py`
- `python -m pytest tests/test_planning_loop_guard.py -q` -> `6 passed`
- `python -m pytest tests/test_planning_through_controller_fake_model.py -q` -> `22 passed`
- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py tests/test_sprint5_paid_blocker_regression.py -q` -> `7 passed`
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q` -> `34 passed`
- `python -m pytest tests/test_context_manager.py tests/test_llm_runtime_controller_contract.py -q` -> `29 passed`
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q` -> `47 passed`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_fake_llm_factory.py tests/test_backend_event_sequences.py tests/test_recording_codegen_truth_contract.py -q` -> `67 passed`

Evidence:
- The live paid retry failure now has a cheap backend reproduction and a bounded stop path.
- No paid E2E has been rerun after the fix.

Paid E2E status: not run
S5-013 retry readiness: yes
