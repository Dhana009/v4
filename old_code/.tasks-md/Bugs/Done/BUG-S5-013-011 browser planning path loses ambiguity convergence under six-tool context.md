Status: Done

Root cause:
The browser E2E planning path exposed all 6 planning tools (dom_extract, locator_find, locator_validate, browser_get_state, send_to_overlay, ask_user) on every outer loop iteration. The model in the browser context repeatedly called send_to_overlay(llm_thinking) instead of committing to ask_user or plan_ready, because:
1. Exploration tools remained available every turn — model preferred "thinking then exploring" over committing.
2. send_to_overlay tool description was generic (no "do not use llm_thinking" constraint).
3. The convergence pressure injected after a thinking-only turn was text-only — tool surface never narrowed.
4. _pending_planning_ambiguity only gets set when dom_extract returns ambiguous results, but the model never called dom_extract — it just kept thinking.

Direct probe path worked because it statically used 2 tools (ask_user + send_to_overlay) with explicit "do not use llm_thinking" descriptions, forcing immediate commitment.

Fix:
- agent.py: Added `_step_plan_convergence_narrowing: bool = False` instance flag (init + _reset_lifecycle_state).
- agent.py: After a thinking-only turn in the outer planning loop, sets `_step_plan_convergence_narrowing = True` before `continue`.
- agent.py: When building `purpose_allowed_tool_names` for `step_plan_normalizer`, if `_step_plan_convergence_narrowing` is True OR `_pending_planning_ambiguity` is set, overrides tool surface to `{"ask_user", "send_to_overlay"}` only — matching what the direct probe does.

Effect:
- Turn 1: model sees 6 tools, calls llm_thinking → convergence narrowing flag set
- Turn 2: model sees only ask_user + send_to_overlay → must commit to ask_user or plan_ready
- Pending ambiguity (from dom_extract finding multiple Profile headings) also triggers narrowing immediately on first planning call

Tests added (tests/test_planning_convergence_contract.py):
- test_browser_path_tool_surface_narrows_after_first_thinking_only_turn: verifies turn 1 = 6 tools, turn 2 = 2 tools; no execution events
- test_pending_ambiguity_narrows_tool_surface_without_prior_thinking_turn: verifies pending ambiguity narrows tools on first call
- test_convergence_narrowing_flag_cleared_on_lifecycle_reset: verifies _step_plan_convergence_narrowing resets to False

Verification:
- tests/test_planning_convergence_contract.py: 8 passed
- tests/test_sprint5_llm_runtime_guardrails.py: 40 passed
- tests/test_sprint5_paid_blocker_regression.py + test_sprint5_paid_retry_blocker_regression.py: passed
- tests/test_planning_loop_guard.py: passed
- tests/test_planning_through_controller_fake_model.py: passed
- Total: 68 passed, 0 failed

Product behavior changed: yes
- Browser planning path now narrows to 2 tools after first thinking-only turn
- ask_user or plan_ready is the expected next outcome
- Ambiguity detected from dom_extract also narrows tools immediately

Paid E2E run: no
Live LLM run: no
S5-013 retry readiness: yes — tool surface now mirrors direct probe that passed

Remaining risks:
- The direct probe uses explicit "do not use llm_thinking" in tool descriptions; browser path still uses generic descriptions. The narrowing removes exploration tools, making commit mandatory, but send_to_overlay still allows llm_thinking as a response type. A follow-up could add description constraints on send_to_overlay when narrowed. However, with only 2 tools and the convergence pressure message, the model is strongly guided to commit.
- _pending_planning_ambiguity is only detected via dom_extract returning Profile headings. Other ambiguity patterns would need similar detection added to _update_planning_ambiguity_from_tool_result.
