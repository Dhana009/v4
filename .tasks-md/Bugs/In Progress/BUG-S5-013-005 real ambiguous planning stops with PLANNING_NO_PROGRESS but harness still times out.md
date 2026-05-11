Status: In Progress
Sprint: Sprint 5
Owner: AutoWorkbench

Source/evidence:
- Paid retry artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-152632-66463/`
- `failure-context.json` shows `stage=llm_response_seen`, `reason=Timed out waiting for plan review or clarification`, `llm_triggered=true`, and `observed_event_types=[]`.
- `backend.tail.log` shows the backend exited planning with `[PHASE] from=planning to=failed reason=planning_no_progress step_id=none`.
- The loop is bounded now, but the harness still does not receive a terminal signal it accepts.

Problem:
- The ambiguous planning flow still fails acceptance because the E2E harness times out waiting for plan review or clarification even after the backend stops with `planning_no_progress`.
- The backend no longer loops forever, but the no-progress stop is not surfaced in a way that the live harness recognizes as terminal.

Root cause hypothesis:
- The planning-loop guard is working, but the no-progress rejection is not reaching the acceptance surface in the form the harness expects.
- Either the runtime-rejected event is not emitted, is not forwarded, or the frontend/harness does not treat the current failed phase as terminal.

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

Verification commands/results:
- `python -m pytest tests/test_planning_loop_guard.py -q` -> `6 passed`
- `python -m pytest tests/test_planning_through_controller_fake_model.py -q` -> `22 passed`
- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py tests/test_sprint5_paid_blocker_regression.py -q` -> `7 passed`
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q` -> `34 passed`
- `python -m pytest tests/test_context_manager.py tests/test_llm_runtime_controller_contract.py tests/test_telemetry_breakdown.py tests/test_token_report.py -q` -> `76 passed`
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q` -> failed with `TimeoutError: Timed out waiting for plan review or clarification`

Paid E2E status: not run after bug filing
S5-013 retry readiness: no
