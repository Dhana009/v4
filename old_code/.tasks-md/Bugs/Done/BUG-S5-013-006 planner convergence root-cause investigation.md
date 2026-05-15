# BUG-S5-013-006 Planner Convergence Root-Cause Investigation

**Status:** Done
**Closed:** 2026-05-12
**Sprint:** Sprint 5
**Owner:** Dhanunjaya
**Artifact reviewed:** test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-155347-19482/
**Resolution:** Resolved via BUG-S5-013-011 (tool-surface narrowing) + BUG-S5-013-012 (schema strip + forced tool_choice). Paid E2E (artifact 20260512-184303-75719) shows `ask_user` terminal output.

---

## Problem statement

The `step_plan_normalizer` planning loop never produced `plan_ready` or `ask_user`. After 4 LLM calls (llm_001–llm_004), the guard fired `PLANNING_NO_PROGRESS` and the run entered `phase=failed`. The test `llm_required_ambiguous_action_flow` expected the planner to either produce a plan or ask for clarification given an ambiguous page (3 "Profile" headings, no obvious single target), but the real model instead browsed the DOM without committing.

The cheap fake-model tests did not catch this because:
1. The fake test for repeated `llm_thinking` has a broken assertion: the guard intercepts `llm_thinking` turns **before** tool execution, so `_send("llm_thinking")` is never emitted; the test asserts `message_types.count("llm_thinking") == 2` which is always false.
2. No test validates that the real model sequence (llm_thinking → browser_get_state → dom_extract → no terminal output) is caught and generates PLANNING_NO_PROGRESS.
3. No test validates that the planner converges within N turns when context is genuinely ambiguous.

---

## What we expected

Given: ambiguous page with 3 Profile sections, user intent unspecified.
Expected: model calls `ask_user(question="...")` within 1–2 turns (clarification path), OR calls `send_to_overlay(message_type="plan_ready", ...)` with a best-guess plan.
The TERMINAL_OUTPUT_REQUIREMENT in the prompt pack explicitly demands one of these.

---

## What actually happened

| Turn | Call ID | Model output | Tool executed | Tool result |
|------|---------|-------------|---------------|-------------|
| 1 | llm_001 | `send_to_overlay(message_type="llm_thinking")` | YES — _tool_send_to_overlay called, `{"sent": true}` returned | Guard: thinking_only=True, convergence pressure injected |
| 2 | llm_002 | `browser_get_state({})` | YES | `{"url": "…/ambiguous-actions.html", "title": "Ambiguous Actions Fixture"}` |
| 3 | llm_003 | `dom_extract({"scope": "page"})` | YES | 3 Profile headings, no CTAs |
| 4 | llm_004 | 75 output tokens, no terminal tool call | N/A | Guard fires PLANNING_NO_PROGRESS |

Key observations:
- `llm_001` emitted `llm_thinking` and the tool was **actually executed** (`{"sent": true}`). The guard detected thinking_only and injected a convergence pressure message.
- Despite convergence pressure, `llm_002` called `browser_get_state` (a non-terminal tool, not llm_thinking). This **reset the consecutive_thinking_only counter** but did NOT reset `planning_turns_without_terminal_output`.
- `llm_003` called `dom_extract` — again non-terminal.
- `llm_004` produced 75 tokens of output with no tool call at all — not plan_ready, not ask_user.
- After 4 turns without a terminal output, `MAX_PLANNING_TURNS_WITHOUT_TERMINAL_OUTPUT` (3) was exceeded.

FIRST-CLASS TESTING GAP: The artifact does not contain the actual model input payload for llm_004 (the final turn after dom_extract). We do not know what the model produced as text content. The `backend.log` does not capture model assistant text output, only tool calls and results. **No redacted prompt/payload is stored per LLM call.** Without the final assistant text we cannot determine whether the model produced ambiguous reasoning, a confused plan proposal, or simply refused to call ask_user.

---

## Evidence

- `backend.log` tool call sequence: llm_thinking → browser_get_state → dom_extract → (no terminal call)
- `token-report.json`: `output_tokens=75` on llm_004 (text was generated but no tool used)
- `failure-context.json`: `PLANNING_NO_PROGRESS`, `stage=llm_response_seen`, `runtime_rejected`
- `dom_extract` result: "Ambiguous Actions Fixture headings: Profile Settings, Billing Profile, Shipping Profile ctas: " — three profiles, no CTAs, genuinely ambiguous
- Prompt pack `TERMINAL_OUTPUT_REQUIREMENT` is present and correctly worded
- Tool schema `send_to_overlay` description explicitly names `plan_ready` as the terminal call and `llm_thinking` as at-most-once
- `ask_user` is in the 6 allowed tools for `step_plan_normalizer`
- Fake test `test_repeated_llm_thinking_stops_before_harness_timeout` is CURRENTLY FAILING: asserts `message_types.count("llm_thinking") == 2` but actual is 0, because the guard short-circuits before tool dispatch

---

## Root-cause hypotheses

| Rank | Hypothesis | Evidence for | Evidence against | Confidence | Test needed |
|------|-----------|--------------|-----------------|------------|-------------|
| 1 | Ambiguous fixture is genuinely ambiguous; model correctly should ask_user but the DOM tool results gave no target cue, so model produced text with no tool call (content-only response in planning mode is not caught as a terminal path) | dom_extract shows 3 profile sections, no CTAs; output_tokens=75 on final turn with no tool call; 75 tokens is enough for a question or a plan | TERMINAL_OUTPUT_REQUIREMENT explicitly says call ask_user when ambiguous | HIGH | Test: convergence contract — planner must produce plan_ready or ask_user within 3 turns even when context is ambiguous, using fake adversarial model that produces text-only final response |
| 2 | Tool schema unclear: plan_ready hidden inside send_to_overlay enum, model does not perceive it as a distinct "exit" action | send_to_overlay has 7 enum values; plan_ready is buried; ask_user is a separate top-level tool and is clearer; model chose browser exploration tools instead of ask_user | send_to_overlay description explicitly says "required terminal call for step_plan_normalizer"; ask_user is also clearly available | MEDIUM | Test: tool contract clarity — generate tool schema text and assert ask_user and plan_ready are unambiguously presented as terminal options |
| 3 | Convergence pressure message was injected but did not change the model's behavior; model used browser/DOM tools as a proxy for "being helpful" and then produced content-only output | llm_002 after convergence pressure still used browser_get_state instead of ask_user | Content-only (non-tool) response on turn 4 is not the same as llm_thinking; the model may have tried to respond but chose text over tool call | MEDIUM | Test: content-only planning response is also counted as non-terminal by planning loop guard (currently: content-only response with no tool_calls is NOT caught by guard as thinking_only; it falls through to the turn counter) |
| 4 | Dynamic context insufficient: DYNAMIC_PLANNING_CONTEXT was empty for most fields (page_summary, queued_steps, validated_locators all empty) so model had no anchor and explored DOM to fill in context | Context fields in dynamic suffix were all empty for this test; model had to call tools to understand the page | Model was supposed to ask_user when ambiguous, not explore DOM | MEDIUM | Test: step_plan_normalizer dynamic context includes non-empty page_summary when page is loaded; if blank, model is expected to ask_user not explore |
| 5 | Prompt pack TERMINAL_OUTPUT_REQUIREMENT too weak: says "You MAY call llm_thinking at most once" but after convergence pressure the model switched to DOM tools; the prompt didn't explicitly forbid DOM exploration in planning when ambiguous | DOM tools (browser_get_state, dom_extract) are in PLANNING_SAFE_TOOL_NAMES and are not forbidden | Prompt says "Ask clarification when ambiguous" but doesn't say "do not call DOM tools when page context is ambiguous" | LOW | Test: prompt pack acceptance test — assert that TERMINAL_OUTPUT_REQUIREMENT includes a clear prohibition on continued DOM tool calls after convergence pressure |
| 6 | Guard does not count content-only (no-tool) LLM responses as a separate failure mode: turn 4 produced 75 tokens of text with no tool call; this counts as a planning_turn_without_terminal_output but is not separately detected and logged as "content_only_no_terminal" | This is not separately logged or surface in test assertions | The overall guard counter covers it; the turn limit fired correctly | LOW | The guard works; but the failure mode is not reported distinctly to aid debugging |

---

## Tests that missed it

1. `test_repeated_llm_thinking_stops_before_harness_timeout` (CURRENTLY FAILING)
   - Asserts `message_types.count("llm_thinking") == 2` — incorrect because the guard intercepts before tool dispatch. The `_send("llm_thinking")` is never called. The test assertion is wrong relative to the actual runtime behavior.
   - The test correctly validates that 3 llm_thinking turns → PLANNING_NO_PROGRESS, but the assertion about sent messages is stale and reflects an older design where the tool was dispatched before the guard checked.

2. No test validates the real failure mode: model makes llm_thinking turn 1, then DOM exploration turns 2-3, then content-only turn 4 → PLANNING_NO_PROGRESS.

3. No test validates that content-only (no-tool) response in planning mode is counted as non-terminal (it is, via planning_turns_without_terminal_output, but no test asserts this path).

4. No test validates that the planner must reach plan_ready or ask_user within N turns for an ambiguous fixture using realistic fake model behavior (llm_thinking → DOM tools → text-only).

5. No test validates that the generated tool schema text makes ask_user an obvious terminal choice when the page is ambiguous.

6. No test captures or snapshots the actual model prompt payload; future investigation of llm_004's 75-token text output is impossible.

---

## Missing test layer

Primary missing category: **planner convergence contract test** — an integration test that verifies `step_plan_normalizer` reaches `plan_ready` or `ask_user` within N turns under a fake model that behaves like the real gpt-4o-mini did (llm_thinking + DOM exploration + text-only). This would have caught both the real failure and the broken assertion.

Secondary missing category: **payload capture test** — paid E2E runs do not capture the actual assistant response text for non-tool turns. When the model produces 75 tokens of text with no tool call, we cannot see what it said. This is a first-class debugging gap.

Tertiary missing category: **tool contract clarity test** — the generated tool schema text (584 tokens) has never been asserted to present ask_user and plan_ready as unambiguously terminal from the model's perspective.

---

## Recommended next fix ticket

**Title:** BUG-S5-013-007 Convergence contract: planner must reach plan_ready or ask_user within 3 turns under adversarial fake model

**Tests first:**
1. `test_step_plan_normalizer_convergence_contract_with_adversarial_fake_model` — fake model sequence: [llm_thinking, browser_get_state, dom_extract, text_only] → assert PLANNING_NO_PROGRESS fires and runtime_rejected is sent
2. `test_repeated_llm_thinking_stops_before_harness_timeout` assertion fix: assert `message_types.count("llm_thinking") == 0` (not 2), because guard intercepts before tool dispatch
3. `test_planning_guard_counts_content_only_response_as_non_terminal` — guard should count text-only LLM response as planning_turn_without_terminal_output (verify existing behavior with explicit test)
4. `test_tool_schema_text_makes_ask_user_and_plan_ready_clearly_terminal` — render the 6 planning tools, assert description text unambiguously names both as terminal exits
5. `test_paid_artifact_includes_assistant_text_for_all_turns` — E2E harness captures and stores assistant text output (even if no tool call) for each LLM turn

**Runtime/prompt/tool contract change:**
- Consider: when `dom_extract` result reveals genuinely ambiguous page (3+ same-type sections, no CTAs), inject a clarification pressure message: "Page is ambiguous. You MUST call ask_user now."
- Consider: change prompt pack to explicitly state "Do NOT call DOM exploration tools a second time during planning. If the page is ambiguous after one dom_extract, call ask_user immediately."
- Capture: store assistant text output in artifact even when no tool call is made

**Expected acceptance criteria:**
- Fake adversarial model test passes without modifying guard limits
- Broken assertion in `test_repeated_llm_thinking_stops_before_harness_timeout` is fixed
- Tool schema text test passes
- Next paid run: either model calls ask_user within 2 turns, or PLANNING_NO_PROGRESS fires with assistant text captured for debugging

---

## Recommended tests before next paid run

| Gap | Missing test | Test file | Fake/live? | Required before next paid run? |
|-----|-------------|-----------|------------|-------------------------------|
| Planner convergence contract (adversarial: llm_thinking → DOM tools → text-only) | `test_step_plan_normalizer_convergence_contract_with_adversarial_fake_model` | tests/test_planning_loop_guard.py or new tests/test_planning_convergence_contract.py | Fake | YES |
| Broken assertion in `test_repeated_llm_thinking_stops_before_harness_timeout` | Fix assertion: llm_thinking count should be 0, not 2 | tests/test_planning_through_controller_fake_model.py | Fake | YES |
| Content-only (no-tool) LLM response counted as non-terminal by guard | `test_planning_guard_counts_content_only_response_as_non_terminal` | tests/test_planning_loop_guard.py | Fake | YES |
| Tool schema clarity: ask_user and plan_ready clearly terminal | `test_tool_schema_text_makes_ask_user_and_plan_ready_clearly_terminal` | tests/test_tool_schema_filter.py or new tests/test_tool_contract_clarity.py | Fake | YES |
| Prompt pack TERMINAL_OUTPUT_REQUIREMENT assertion | `test_step_plan_normalizer_prompt_pack_forbids_repeated_dom_exploration` | tests/test_prompt_pack_safety_rules.py | Fake | YES |
| Payload capture: assistant text for non-tool turns | `test_paid_artifact_captures_assistant_text_for_content_only_turns` | tests/test_e2e_harness.py | Fake harness + contract | YES — blocks next paid run |
| Dynamic context: page_summary non-empty when page loaded | `test_dynamic_context_page_summary_populated_for_ambiguous_fixture` | tests/test_prompt_pack_builder.py | Fake | YES |

---

## Additional gaps found

1. **Broken test (currently failing):** `tests/test_planning_through_controller_fake_model.py::test_repeated_llm_thinking_stops_before_harness_timeout` asserts `llm_thinking` count == 2 in sent_messages. This is wrong: the guard short-circuits before tool dispatch. The test has been wrong since the guard was changed to intercept before tool execution (commit be9d4c4). This must be fixed before the next paid run to avoid false confidence.

2. **13 other currently failing tests** (as of this investigation): `test_llm_planning_contracts.py`, `test_llm_policy_gateway.py`, `test_llm_specialist_contracts.py` — these are unrelated to this bug but indicate the test suite has broader issues that may mask real regressions.

3. **No model output capture:** The artifact contains tool results but not assistant text for turns with content-only responses. When llm_004 produces 75 tokens, we cannot determine whether the model was trying to propose a plan in text form (incorrect format) or was genuinely stuck. This is a first-class debugging gap.

4. **The real model behavior (llm_thinking → DOM tools → text-only) is not modeled by any existing fake test.** The fake tests only model repeated llm_thinking. The real model's exploitation of DOM tools as a fallback has never been exercised in fake tests.

5. **DYNAMIC_PLANNING_CONTEXT** dynamic suffix fields were empty (page_summary, queued_steps, validated_locators all blank). The model had no pre-computed page context and had to call DOM tools to understand the page. This is a design gap: if the page is loaded, the harness should pre-populate page_summary before calling the planner.

6. **E2E test `test_llm_required_ambiguous_action_flow`** — currently in `tests/e2e/test_llm_required_ambiguous_action_flow.py` — is currently FAILING in the test suite. This confirms the paid run failure is reproducible and the fixture is correctly triggering the convergence failure, but the test does not have a clear expected outcome contract (should the test expect ask_user, plan_ready with best guess, or PLANNING_NO_PROGRESS?).
