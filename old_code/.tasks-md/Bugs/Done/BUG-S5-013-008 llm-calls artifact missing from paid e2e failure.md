Status: Done

Root cause:
- `tests/e2e/harness.py` already had `build_llm_calls_artifact()` and `write_llm_calls_artifact()`, but the close/finalize path never invoked them, so paid failure artifacts could contain token telemetry without the required `llm-calls.json`.
- The artifact builder also kept only a narrow subset of fields, so even when wired it would not have preserved the full safe debugging shape required for the paid retry.

Fix:
- `E2ESession.close()` now always writes `llm-calls.json` into the exact artifact directory on both success and failure paths.
- The harness now parses `[LLM_CALL]` records from backend stdout and persists a redacted per-call artifact even if the test fails before `plan_ready`.
- The artifact schema now captures call metadata, safe tool schema summaries, assistant content-only text, tool call names, safe arguments, finish reason, usage when present, and error metadata on failed calls.

Artifact behavior:
- `tests/e2e/harness.py` now declares `llm-calls.json` as a first-class artifact alongside `token-report.json`.
- If backend stdout contains no call records, the harness still writes `llm-calls.json` as `[]` rather than omitting the file.
- Bearer tokens and similar secrets are redacted before writing the artifact.

Tests:
- `tests/test_e2e_harness.py`
  - `test_session_close_writes_empty_token_report_when_telemetry_is_missing`
  - `test_payload_capture_redacts_tool_call_args_summary`
  - `test_paid_artifact_captures_tool_schema_summary_fields`
  - `test_session_close_writes_llm_calls_artifact_on_failure_before_plan_ready`
- `tests/test_sprint5_llm_runtime_guardrails.py`
  - `test_llm_calls_artifact_requirement_writes_even_empty_file`

Commands/results:
- `python -m py_compile agent.py tests/e2e/harness.py tests/test_e2e_harness.py tests/test_planning_convergence_contract.py tests/test_tool_contract_clarity.py tests/test_planning_loop_guard.py tests/test_planning_through_controller_fake_model.py tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_sprint5_llm_runtime_guardrails.py`
  - pass
- `python -m pytest tests/test_e2e_harness.py -q`
  - `68 passed`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_sprint5_llm_runtime_guardrails.py -q`
  - `53 passed`
- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py tests/test_sprint5_paid_blocker_regression.py -q`
  - `7 passed`

Additional gaps found:
- The existing artifact builder only preserved a minimal subset of fields.
- Tool-call argument summaries were not redacted before artifact writing.
