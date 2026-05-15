Status: Done

Root cause:
- Full paid browser E2E was being used as the first live-model behavioral check for ambiguous planning, which is too expensive and too noisy for diagnosing prompt/tool convergence failures.
- The repo had no cheaper live-model seam that exercised `step_plan_normalizer` directly with prompt/tool artifacts and bounded cost.

Fix:
- Added `tests/test_real_llm_planner_contract.py` as a paid/live contract probe for ambiguous planning.
- The probe drives `LLMRuntimeController.call_with_raw_response()` directly with a minimal ambiguous Profile scenario and a narrow tool surface (`ask_user`, `send_to_overlay`) and never launches browser or Playwright.
- The test is skipped by default unless `RUN_PAID_LLM_CONTRACT=1`; it also requires a valid `OPENAI_API_KEY`.
- The probe now prefers repo `.env` key precedence to match the product startup path and writes provider error message/type into the artifact for direct diagnosis.

Probe behavior:
- Contract scenario:
  - User intent: `Click the Edit button in the Profile section`
  - Ambiguous options:
    - `Profile - John Smith - Edit`
    - `Profile - Jane Smith - Edit`
    - `Profile - Student Profile - Edit`
- Expected pass:
  - terminal tool call is `ask_user`
- Recorded artifacts:
  - `llm-calls.json`
  - `prompt-tool-summary.json`
  - `token-report.json`
  - `assertion-result.json`
- Artifact location:
  - `test-results/llm-contract/step_plan_normalizer_ambiguous_profile-<timestamp>/`

Tests:
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_tool_contract_clarity.py -q`
  - `23 passed`
- `python -m pytest tests/test_planning_convergence_contract.py tests/test_planning_loop_guard.py -q`
  - `11 passed`
- `python -m pytest tests/test_sprint5_llm_runtime_guardrails.py tests/test_e2e_harness.py -q`
  - `101 passed`
- `python -m pytest tests/test_real_llm_planner_contract.py -q`
  - `1 skipped`

Commands/results:
- Default skip verification:
  - `python -m pytest tests/test_real_llm_planner_contract.py -q`
  - result: skipped without `RUN_PAID_LLM_CONTRACT=1`
- First live attempt:
  - `RUN_PAID_LLM_CONTRACT=1 python -m pytest tests/test_real_llm_planner_contract.py -q`
  - artifact: `test-results/llm-contract/step_plan_normalizer_ambiguous_profile-20260511-124958/`
  - result: failed before planner behavior with `APIConnectionError`
- Escalated live attempt after sandbox/network suspicion:
  - `RUN_PAID_LLM_CONTRACT=1 python -m pytest tests/test_real_llm_planner_contract.py -q`
  - artifact: `test-results/llm-contract/step_plan_normalizer_ambiguous_profile-20260511-125024/`
  - result: failed before planner behavior with `AuthenticationError`
- Follow-up test-only fix:
  - changed key precedence to prefer repo `.env` over stale shell env and added exact provider error capture to artifacts
- No additional live rerun performed in this task after the test seam fix.

Additional gaps found:
- The first live probe attempts did not produce valid planner behavior evidence because they failed at provider access/authentication before any tool call.
- A fresh single live contract probe is still needed after the repo-key precedence fix to determine whether the real model chooses `ask_user`, `llm_thinking`, or plain text under the narrowed contract.
