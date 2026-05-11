Status: Done

Root cause:
- The planner loop could bound repeated non-terminal turns, but it did not promote obvious DOM ambiguity into a runtime-owned clarification path before the next unproductive planning turn.
- Content-only planning replies were still able to fall through as non-executing success-shaped output instead of being treated as another non-terminal planning turn.

Fix:
- `agent.py` now tracks pending planning ambiguity from `dom_extract` results when multiple plausible Profile-like sections remain.
- When ambiguity is explicit, the next planning turn receives a runtime-owned instruction that says multiple plausible targets were found, `ask_user` is required, plain-text replies are forbidden, and no further DOM exploration should continue.
- If the model still returns non-terminal output instead of a terminal tool call, the runtime forces the clarification path through `ask_user` rather than drifting until another no-progress cycle.
- Content-only planning responses remain non-terminal and cannot be treated as `plan_ready`.
- `llm/tool_definitions.py` now makes the `ask_user` terminal clarification contract explicit for ambiguous targets.

Convergence behavior:
- Clear DOM ambiguity now prefers `ask_user` with options/distinguishing labels derived from the `dom_extract` result.
- `plan_ready` remains valid only when enough context exists.
- `PLANNING_NO_PROGRESS` remains a controlled terminal failure, not a success condition.
- No success lifecycle can occur before confirmation because the clarification path never emits `step_recorded`, `code_update`, `run_completed`, or browser-changing actions.

Tests:
- `tests/test_planning_convergence_contract.py`
  - adversarial sequence with `dom_extract` returning three Profile sections routes to clarification without timing out
  - ambiguity instruction includes multiple plausible targets, `ask_user` requirement, options, and stop-DOM-exploration pressure
  - content-only planning response remains non-terminal
  - no success lifecycle before confirmation
  - bounded planning turns remain enforced
- `tests/test_tool_contract_clarity.py`
  - `ask_user` description requires terminal clarification and forbids plain-text clarification
- `tests/test_planning_through_controller_fake_model.py`
  - malformed/content-only planning output fails closed with `PLANNING_NO_PROGRESS` rather than being accepted as success
- `tests/test_sprint5_llm_runtime_guardrails.py`
  - ambiguity path stays on `ask_user` or controlled terminal failure
  - content-only planning output is not accepted as success

Commands/results:
- `python -m py_compile agent.py tests/e2e/harness.py tests/test_e2e_harness.py tests/test_planning_convergence_contract.py tests/test_tool_contract_clarity.py tests/test_planning_loop_guard.py tests/test_planning_through_controller_fake_model.py tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_sprint5_llm_runtime_guardrails.py`
  - pass
- `python -m pytest tests/test_planning_convergence_contract.py tests/test_tool_contract_clarity.py -q`
  - `8 passed`
- `python -m pytest tests/test_planning_loop_guard.py tests/test_planning_through_controller_fake_model.py -q`
  - `28 passed`
- `python -m pytest tests/test_context_manager.py tests/test_llm_runtime_controller_contract.py tests/test_backend_event_sequences.py tests/test_event_sequence_contract.py tests/test_event_contract.py -q`
  - `46 passed`
- `python -m pytest tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_fake_llm_factory.py tests/test_telemetry_breakdown.py tests/test_token_report.py tests/test_recording_codegen_truth_contract.py -q`
  - `94 passed`

Additional gaps found:
- The current convergence pressure only addresses repeated `llm_thinking`.
- Clear `dom_extract` ambiguity can still degrade into content-only planning output instead of clarification.
