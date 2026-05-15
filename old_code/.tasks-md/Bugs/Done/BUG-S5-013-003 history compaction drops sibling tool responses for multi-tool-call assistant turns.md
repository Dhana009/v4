Status: Done

Sprint:
- Sprint 5

Owner:
- Codex

Source/evidence:
- Live S5-013 paid retry failure: OpenAI Chat Completions 400 for missing `tool` response messages after an assistant `tool_calls` turn.
- Runtime diagnosis: compacted `step_plan_normalizer` history could retain an assistant message with multiple `tool_calls` while dropping one sibling `tool` response.

Root cause:
- `ContextManager.prepare_messages(...)` compacted planning history before the provider call.
- For `step_plan_normalizer`, the compacted window could preserve a multi-tool-call assistant turn and only the most recent matching tool response.
- That violated the Chat Completions invariant that every `tool_call_id` in an assistant `tool_calls` message must have a corresponding `tool` response message.

Fix:
- Added purpose-scoped tool-chain restoration in `runtime/context_manager.py`.
- When `step_plan_normalizer` or `locator_specialist` history includes a selected assistant turn with multiple `tool_calls`, the context manager restores the full assistant/tool bundle before sending messages to the provider.
- Restoration is not applied to recovery purposes, so recovery evidence handling stays unchanged.

Regression tests:
- `tests/test_context_manager.py::test_step_plan_normalizer_keeps_complete_multi_tool_call_chain`
- `tests/test_llm_runtime_controller_contract.py::test_controller_call_with_raw_response_sends_complete_multi_tool_call_history`

Verification commands/results:
- `python -m py_compile runtime/context_manager.py tests/test_context_manager.py tests/test_llm_runtime_controller_contract.py`
  - passed
- `python -m pytest tests/test_context_manager.py tests/test_llm_runtime_controller_contract.py -q`
  - 29 passed
- `python -m pytest tests/test_planning_through_controller_fake_model.py -q`
  - 21 passed
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q`
  - 34 passed
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_fake_llm_factory.py tests/test_backend_event_sequences.py tests/test_recording_codegen_truth_contract.py -q`
  - 67 passed

Paid E2E status:
- not run

S5-013 retry readiness:
- yes
