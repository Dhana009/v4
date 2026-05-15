Status: Done
Sprint: Sprint 5
Owner: AutoWorkbench

Source/evidence:
- Paid retry artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-152632-66463/`
- `failure-context.json` shows `stage=llm_response_seen`, `reason=Timed out waiting for plan review or clarification`, `llm_triggered=true`, and `observed_event_types=[]`.
- `backend.tail.log` shows the backend exited planning with `[PHASE] from=planning to=failed reason=planning_no_progress step_id=none`.
- The loop is bounded now, but the harness still does not receive a terminal signal it accepts.
- Fix verification shows the backend now emits and logs a terminal `[RUNTIME_REJECTED]` marker for `PLANNING_NO_PROGRESS`, and the E2E harness stops on that marker instead of timing out.

Problem:
- The ambiguous planning flow previously failed acceptance because the E2E harness timed out waiting for plan review or clarification even after the backend stopped with `planning_no_progress`.
- The backend no longer loops forever, and the no-progress stop is now surfaced through a terminal backend rejection marker that the harness observes.

Root cause hypothesis:
- The planning-loop guard was working, but the no-progress rejection was not reaching the acceptance surface in a form the harness observed.
- The fix now emits a compact terminal backend rejection marker and the harness stops on it.

Scope:
- Verify the `planning_no_progress` stop is emitted as a terminal event on the live planning path.
- Verify the harness can observe the terminal no-progress signal instead of waiting for clarification.
- Keep the fix narrow to the planning acceptance surface.

Out of scope:
- Paid E2E reruns.
- Live LLM retries.
- Prompt rewrites as the primary fix.
- Broad planning-loop refactors.
- Frontend redesign.

Required unit tests:
- `tests/test_planning_loop_guard.py`
- `tests/test_backend_event_sequences.py`

Required contract tests:
- `tests/test_planning_through_controller_fake_model.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_token_report.py`
- `tests/test_telemetry_breakdown.py`

Required integration tests:
- `tests/test_sprint5_paid_retry_blocker_regression.py`
- `tests/test_sprint5_paid_blocker_regression.py`
- `tests/test_sprint5_llm_runtime_guardrails.py`
- `tests/test_e2e_harness.py`

Acceptance criteria:
- The live ambiguous planning flow either reaches `plan_ready`/clarification or fails fast with a surfaced terminal no-progress signal.
- The harness no longer times out waiting for plan review or clarification when the backend has already stopped.
- No infinite or unbounded `llm_thinking` loop remains.
- The terminal no-progress path is observable in artifact evidence.

Evidence:
- Latest retry artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-152632-66463/`
- Backend log evidence: `[PHASE] from=planning to=failed reason=planning_no_progress step_id=none`
- Harness evidence: `Timed out waiting for plan review or clarification`
- `observed_event_types=[]` in `failure-context.json`
- Fix evidence: backend logs now include `[RUNTIME_REJECTED] rejection_code=PLANNING_NO_PROGRESS ...` and the harness test stops on that terminal marker.

Verification commands/results:
- `python -m pytest tests/test_planning_loop_guard.py -q` -> `6 passed`
- `python -m pytest tests/test_planning_through_controller_fake_model.py -q` -> `22 passed`
- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py tests/test_sprint5_paid_blocker_regression.py -q` -> `7 passed`
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q` -> `34 passed`
- `python -m pytest tests/test_context_manager.py tests/test_llm_runtime_controller_contract.py tests/test_telemetry_breakdown.py tests/test_token_report.py -q` -> `76 passed`
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q` -> failed with `TimeoutError: Timed out waiting for plan review or clarification`
- `python -m py_compile agent.py tests/e2e/harness.py tests/test_planning_through_controller_fake_model.py tests/test_e2e_harness.py` -> passed
- `python -m pytest tests/test_planning_through_controller_fake_model.py tests/test_e2e_harness.py -q` -> `83 passed`
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q` -> `34 passed`
- `python -m pytest tests/test_context_manager.py tests/test_llm_runtime_controller_contract.py -q` -> `29 passed`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_event_sequence_contract.py tests/test_event_contract.py -q` -> `17 passed`
- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py tests/test_sprint5_paid_blocker_regression.py -q` -> `7 passed`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_fake_llm_factory.py tests/test_recording_codegen_truth_contract.py -q` -> `63 passed`
- `python -m pytest tests/test_backend_event_sequences.py -q` -> `4 passed`

Paid E2E status: not run after bug filing
S5-013 retry readiness: yes

Additional gaps found:
- None found.
