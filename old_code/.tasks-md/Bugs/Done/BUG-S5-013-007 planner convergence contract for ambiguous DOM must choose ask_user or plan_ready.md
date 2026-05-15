# BUG-S5-013-007: Planner Convergence Contract for Ambiguous DOM Must Choose ask_user or plan_ready

- **Status:** Done
- **Sprint:** 5
- **Owner:** Claude Code
- **Source evidence:** paid artifact `llm_required_ambiguous_action_flow-20260511-155347-19482`

---

## Root Cause

Three distinct gaps caused the live model to never call ask_user or plan_ready:

1. **Content-only response treated as terminal** — `planning_loop_guard.py` line 140-141 set
   `terminal_reason = "final_text"` for any content-only (no tool_calls) response. This meant
   the guard did NOT increment `planning_turns_without_terminal_output` and never fired for
   content-only turns. The agent then emitted `llm_result` accepting the text as planning success.

2. **ask_user tool description too generic** — "Ask user a question and wait for their response"
   gave no signal that it is the required terminal when targets are ambiguous. The model had no
   schema-level guidance to use it instead of continued DOM exploration.

3. **Prompt pack missing AMBIGUITY_RULE** — the stable prefix had TERMINAL_OUTPUT_REQUIREMENT
   (from prior work) but no explicit rule about what to do when multiple plausible targets exist.
   No instruction said "call ask_user immediately when ambiguity is established."

Secondary: broken test assertion (`llm_thinking count == 2`) masked the guard-before-dispatch
behavior since commit be9d4c4.

---

## Fix

### 1. runtime/planning_loop_guard.py
Removed the `if not raw_tool_calls and content: terminal_reason = "final_text"` branch.
Content-only responses are now non-terminal — they increment `planning_turns_without_terminal_output`
and the guard will fire PLANNING_NO_PROGRESS if the model keeps producing them.

### 2. llm/tool_definitions.py
Updated ask_user description to:
- State it is "the required terminal call when target element, page section, or required data is ambiguous"
- Mention "multiple plausible targets"
- Say "Do not continue DOM exploration after ambiguity is established"

### 3. runtime/prompt_pack_builder.py
Added to `_STEP_PLAN_NORMALIZER_STABLE_PREFIX`:
- `AMBIGUITY_RULE` section: tells model to call ask_user immediately when multiple plausible targets found
- Plain-text prohibition: "Do not respond with plain text instead of a tool call"

### 4. tests/test_planning_through_controller_fake_model.py
Fixed broken assertion: `llm_thinking count == 2` → `llm_thinking count == 0`
(guard fires before tool dispatch; thinking tool calls are never dispatched to `_send`)

### 5. tests/e2e/harness.py
- Added `build_llm_calls_artifact()` and `write_llm_calls_artifact()` for redacted payload capture
- Added Bearer token regex to `_REDACTION_REGEX_RULES`

---

## Convergence Contract (What Model Is Now Expected to Do)

In planning mode (step_plan_normalizer):
1. May call `send_to_overlay(message_type="llm_thinking")` at most once
2. Must follow with `send_to_overlay(message_type="plan_ready")` when plan is clear
3. Must call `ask_user` when DOM evidence shows multiple plausible targets
4. Must NOT respond with plain text instead of a tool call
5. Must NOT repeat llm_thinking — doing so triggers PLANNING_NO_PROGRESS
6. Content-only responses (no tool calls) are non-terminal and count toward the no-progress limit

---

## Tool Schema Clarity

- `send_to_overlay`: already stated "terminal call for step_plan_normalizer"; "at most once" for llm_thinking; "MUST follow it with plan_ready or ask_user"
- `ask_user`: now explicitly states it is the required terminal call for ambiguous targets/pages; discourages DOM exploration after ambiguity established

## Prompt Changes

- Added `AMBIGUITY_RULE` section to step_plan_normalizer stable prefix
- Added plain-text prohibition to TERMINAL_OUTPUT_REQUIREMENT

## Payload Capture

- `harness.build_llm_calls_artifact(calls)` builds a redacted list of per-call records
- `harness.write_llm_calls_artifact(artifact_dir, calls)` writes `llm-calls.json`
- Records: call_id, purpose, tool_names, assistant_text (redacted), tool_calls, finish_reason, token_usage
- Redaction covers: sk- tokens, Bearer tokens, OTPs, emails, phones

---

## Acceptance Clarified

- PLANNING_NO_PROGRESS is a controlled failure (guard fires correctly)
- Next paid E2E should show: model calls ask_user on ambiguous fixture, or produces plan_ready
- If model still produces content-only text, guard will fire (non-terminal now counted)
- E2E test acceptance: plan_ready OR ask_user/clarification are both valid passes

---

## Tests Added

### tests/test_planning_convergence_contract.py (new file)
- `test_adversarial_dom_exploration_sequence_terminates_without_timeout`
- `test_content_only_planning_response_is_non_terminal`
- `test_content_only_response_increments_no_progress_counter`
- `test_repeated_content_only_responses_eventually_trigger_no_progress`

### tests/test_tool_contract_clarity.py (new file)
- `test_send_to_overlay_schema_makes_plan_ready_terminal`
- `test_ask_user_schema_makes_clarification_terminal`
- `test_llm_thinking_schema_is_non_terminal_and_limited`

### tests/test_prompt_pack_builder.py (additions)
- `test_prompt_pack_has_terminal_output_requirement`
- `test_prompt_pack_has_ambiguity_rule`
- `test_prompt_pack_forbids_plain_text_planning_response`
- `test_prompt_pack_limits_llm_thinking_repetition`

### tests/test_sprint5_llm_runtime_guardrails.py (additions)
- `test_prompt_pack_includes_terminal_output_requirement`
- `test_prompt_pack_includes_ambiguity_rule`
- `test_ask_user_and_plan_ready_terminal_clarity_present`
- `test_llm_thinking_non_terminal_limited`
- `test_content_only_not_accepted_as_planning_success`

### tests/test_e2e_harness.py (additions)
- `test_paid_artifact_captures_assistant_text_for_content_only_turns`
- `test_paid_artifact_captures_tool_schema_names_exposed`
- `test_payload_capture_does_not_expose_raw_secrets`
- `test_write_llm_calls_artifact_produces_json_file`

### tests/test_planning_through_controller_fake_model.py (fix)
- `test_repeated_llm_thinking_stops_before_harness_timeout` — assertion corrected

---

## Verification Commands/Results

```
python -m pytest tests/ --ignore=tests/e2e -q
# Result: 12 failed (pre-existing, unrelated), 771 passed
```

Pre-existing failures (all unrelated to this bug, present since sprint 5 baseline):
- test_llm_planning_contracts.py: 4 failures
- test_llm_policy_gateway.py: 2 failures
- test_llm_specialist_contracts.py: 6 failures

## Changed Files

- `runtime/planning_loop_guard.py` — content-only no longer terminal
- `llm/tool_definitions.py` — ask_user description updated
- `runtime/prompt_pack_builder.py` — AMBIGUITY_RULE + plain-text prohibition added
- `tests/e2e/harness.py` — build/write_llm_calls_artifact + Bearer redaction rule
- `tests/test_planning_through_controller_fake_model.py` — broken assertion fixed
- `tests/test_planning_convergence_contract.py` — new file
- `tests/test_tool_contract_clarity.py` — new file
- `tests/test_prompt_pack_builder.py` — 4 new tests
- `tests/test_sprint5_llm_runtime_guardrails.py` — 5 new tests
- `tests/test_e2e_harness.py` — 4 new tests

## Commit

*(fill after commit)*

## Additional Gaps Found

- Prompt cache hit rate still 0 (cached_tokens=0 in all paid runs) — separate issue
- Dynamic context (page_summary, queued_steps) still empty on ambiguous fixture — pre-planning hook gap
- Bearer token redaction was missing from harness regex rules (fixed here)
