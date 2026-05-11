# SPRINT-005-CHECKPOINT

**Generated:** 2026-05-11
**HEAD commit:** f8c7cea020d3f46da90e1ae55d9bc364a9ad398a
**Branch:** main (19 commits ahead of origin/main)
**Artifact reviewed:** llm_required_ambiguous_action_flow-20260511-160700-37866 (most recent)

---

## Section 1: Sprint 5 Inventory Table

| Area | Implemented | Tests exist | Real LLM/E2E proven? | Gap |
|---|---|---|---|---|
| controller routing (step_plan_normalizer) | YES — `LLMRuntimeController.call_with_raw_response()` wired in agent.py | YES — test_llm_runtime_controller_contract.py, test_planning_through_controller_fake_model.py | PARTIAL — live path reaches model; does not return plan_ready/ask_user | Model does not converge; content-only/DOM-loop behavior unresolved |
| raw response / tool calls preserved | YES — `call_with_raw_response()` returns raw_response, raw_message, content, tool_calls | YES | PARTIAL — live telemetry shows success=true but model still loops | No test covers content-only (no-tool) response path end-to-end |
| prompt packs | YES — runtime/prompt_packs.py, runtime/prompt_pack_builder.py; step_plan_normalizer.v1 | YES — test_prompt_pack_builder.py, test_prompt_pack_safety_rules.py | YES — prompt_pack_id and prefix_hash confirmed in live telemetry | Tool schema bucket still +42% above baseline; other purposes not packed |
| skill selection | YES — runtime/skill_selector.py, skill_policy.py; compact summaries by default | YES — test_skill_selector.py, test_skill_escalation_contract.py | YES — skill_summary level confirmed live; -50% skill tokens vs baseline | skill_levels absent from token-report.json on early failing runs (fixed later) |
| tool schema filtering | YES — runtime/tool_schema_policy.py; 6 tools exposed for planning | YES — test_tool_schema_filter.py, test_tool_policy_contract.py | YES — TOOL_FILTER confirms 15→6 in every live run | Tool schema bucket is 584 tokens (+42% vs baseline 410); no clarity test for ask_user/plan_ready prominence |
| context compaction | YES — runtime/context_manager.py; compact mode applied | YES — test_context_manager.py | YES — CONTEXT_MANAGER logs show compact mode and budget_status=ok | History tokens grow across turns (238→314→390) but do not explode; assistant turns absent from history (bug or design gap?) |
| correction context | YES — runtime/correction_context.py | YES — test_correction_context.py | NO — no paid run reached correction phase | Not proven in live path at all |
| recovery context | YES — runtime/recovery_context.py | YES — test_recovery_context.py | NO — no paid run reached recovery phase | Not proven in live path at all |
| telemetry / token report | YES — runtime/telemetry.py, runtime/token_report.py; 8 new fields | YES — test_telemetry_breakdown.py, test_token_report.py | YES — all fields confirmed in latest artifact | prefix_hash truncated in early runs; skill_levels absent on some early failing paths; now consistent |
| planning loop guard | YES — runtime/planning_loop_guard.py; max 2 consecutive thinking, max 3 without terminal | YES — test_planning_loop_guard.py (6 tests, all pass) | YES — PLANNING_NO_PROGRESS fires correctly in live run | Guard fires but model reaches guard limit on every live run; convergence never achieved |
| terminal runtime_rejected bridge | YES — RUNTIME_REJECTED marker emitted and harness observes it | YES — test_e2e_harness.py, test_sprint5_paid_retry_blocker_regression.py | YES — latest artifact shows observed_event_types=[runtime_rejected] | E2E test still fails because test expects plan_ready or clarification, not runtime_rejected as success |
| fake LLM suite | YES — tests/fake_llm_factory.py, 18+ tests covering planning/correction/recovery | YES — test_fake_llm_factory.py, test_planning_through_controller_fake_model.py, test_recovery_through_fake_model.py | NO — fake only | Fake model does not simulate the real failure mode (llm_thinking → DOM tools → text-only). One test currently FAILING with wrong assertion |
| paid E2E acceptance | NO — 6+ paid runs, none passed | YES — test_llm_required_ambiguous_action_flow.py (E2E harness) | FAILING — all 6 Sprint 5 paid runs terminated before plan_ready | Current test expects plan_ready or clarification; real model never reaches either |
| payload capture | NO — assistant text for non-tool turns is not stored in artifacts | NO | NO | When model produces content-only response (75 tokens), text is lost; no debugging capability |
| planner convergence contract | NO — no fake test for llm_thinking → DOM tools → text-only sequence | NO | NO (real path hits it every run) | Biggest testing gap; real failure mode not exercised by any fake test |

---

## Section 2: Story Status Table

| Story/Bug | Status | Commit | What it proved | What it did not prove |
|---|---|---|---|---|
| S5-001B | Done | 7a5c557 | step_plan_normalizer routes through LLMRuntimeController; raw_response preserved; tool_calls preserved | Live convergence to plan_ready; behavior under ambiguous page |
| S5-002 | Done | c36fc67 | prompt_pack_id=step_plan_normalizer.v1 appears in live telemetry; system prompt -76% on some runs | Tool schema bucket not reduced; other purposes not covered |
| S5-003 | Done | b9e7673 | Compact skill summaries load by default; skills_loaded=core,actions,download confirmed live | Full-skill escalation path not exercised in live run |
| S5-004 | Done | b9e7673 | Tool filtering 15→6 confirmed in every live TOOL_FILTER log | 584 tool_schema_tokens still above baseline; ask_user/plan_ready clarity not asserted |
| S5-005 | Done | 25cf826 | Correction context module exists and passes unit tests | Not reached in any live paid run |
| S5-006 | Done | 25cf826 | Recovery context module exists and passes unit tests | Not reached in any live paid run |
| S5-007 | Done | 212b7f1 | 8 telemetry fields; token report contains purposes, prompt_pack_ids, model_classes, context_buckets, total_cached_tokens | prefix_hash initially truncated; skill_levels absent on early failing paths |
| S5-012 | Done | 212b7f1 | FakeLLMClient and 18 fake tests; planning/correction/recovery paths testable without paid LLM | Fake does not model real convergence failure (llm_thinking → DOM tools → text-only) |
| S5-013 | Blocked | — | 6+ paid runs demonstrate: live path reaches model, telemetry attribution works, guard fires correctly, terminal event surfaced | Plan_ready or clarification never reached; E2E test acceptance criteria not met |
| S5-014 | Done | (embedded) | Stable prefix strategy defined and implemented | Cache hit rate is 0 in all paid runs (cached_tokens=0) |
| S5-015 | Done | 26ca2f6 | Sprint 5 regression guardrail tests added | 14 tests currently failing in suite (unrelated to guardrails but represent real gaps) |
| BUG-S5-013-001 | Done | c776a1f | raw_response normalizer fix; controller no longer discards tool_calls | Did not fix live convergence |
| BUG-S5-013-002 | Done | fbd34ed | Error surfacing fix; provider 404 now visible instead of generic missing-raw-response | Did not fix live convergence |
| BUG-S5-013-003 | Done | 37d7207 | Compacted tool call chains preserved; model class resolved before provider call | Did not fix live convergence |
| BUG-S5-013-004 | Done | be9d4c4 | Planning loop guard added; PLANNING_NO_PROGRESS fires after 3 non-terminal turns | Guard fires but model still does not call ask_user within turn budget |
| BUG-S5-013-005 | Done | f8c7cea | RUNTIME_REJECTED marker emitted as terminal typed event; harness now observes it instead of timing out | E2E test still fails because test expects plan_ready/clarification, not PLANNING_NO_PROGRESS as terminal |
| BUG-S5-013-006 | In Progress | — | Root-cause investigation complete: model calls llm_thinking → convergence pressure injected → model continues with llm_thinking → guard fires | Fix not yet implemented; broken test assertion identified |

---

## Section 3: Test Coverage Reality Table

| Contract | Test exists? | Test file | Fake or real? | Missing piece |
|---|---|---|---|---|
| model call reaches controller | YES | test_planning_through_controller_fake_model.py | Fake | — |
| raw_response preserved | YES | test_llm_runtime_controller_contract.py | Fake | — |
| tool_call chains preserved | YES | test_planning_through_controller_fake_model.py | Fake | — |
| repeated llm_thinking bounded | YES (but 1 FAILING) | test_planning_loop_guard.py, test_planning_through_controller_fake_model.py | Fake | Broken assertion: test_repeated_llm_thinking_stops_before_harness_timeout asserts llm_thinking count==2 but actual is 0; must be fixed |
| no-progress event surfaced | YES | test_planning_loop_guard.py, test_sprint5_paid_retry_blocker_regression.py | Fake | — (works in fake and live) |
| harness exits on runtime_rejected | YES | test_e2e_harness.py, test_sprint5_paid_blocker_regression.py | Fake harness | E2E test itself does not accept PLANNING_NO_PROGRESS as a valid terminal; acceptance criteria ambiguous |
| prompt packs preserve safety rules | YES | test_prompt_pack_safety_rules.py | Fake | No test for TERMINAL_OUTPUT_REQUIREMENT prohibiting repeated DOM exploration |
| compact skills selected | YES | test_skill_selector.py, test_skill_escalation_contract.py | Fake | — |
| tool schema filtered | YES | test_tool_schema_filter.py, test_tool_policy_contract.py | Fake | No test asserts ask_user and plan_ready appear as clearly terminal in generated schema text |
| correction compact context | YES | test_correction_context.py | Fake | Not proven in any live paid run |
| recovery compact context | YES | test_recovery_context.py | Fake | Not proven in any live paid run |
| real planner chooses plan_ready or ask_user | NO | — | — | No fake test models the real failure sequence; real model never reaches either on live fixture |
| content-only response handled | NO | — | — | No test asserts content-only (no tool_calls) LLM response is counted as non-terminal by guard |
| actual prompt/tool payload captured | NO | — | — | Artifacts do not contain assistant text for non-tool turns; 75-token output from llm_004 is permanently lost |
| tool schema clarity for plan_ready/ask_user | NO | — | — | Never asserted that generated schema text makes ask_user and plan_ready unambiguous exit options |
| ambiguous DOM leads to ask_user | NO | — | — | Real model on ambiguous page (3 Profile headings, no CTAs) never called ask_user; no fake test for this path |

---

## Section 4: Drift Analysis

**What Sprint 5 originally intended:**
Route all planning/correction/recovery calls through LLMRuntimeController with purpose-specific policies, prove token reduction, and validate with controlled paid E2E showing plan_ready or clarification from real LLM on representative flows. Success criteria included at least 2–3 flows passing, token reduction ≤110% of baseline, and correctness unchanged.

**What was built:**
All core wiring stories (S5-001B through S5-006) are implemented and pass fake tests. Telemetry attribution (S5-007) is live and confirmed in paid runs. Planning loop guard (BUG-S5-013-004) and terminal event bridge (BUG-S5-013-005) are implemented. The infrastructure is substantially correct: model is reached, policies applied, guard fires correctly, telemetry emits all fields.

**Where drift occurred:**
1. The paid E2E was run 6+ times before the underlying planner convergence contract was defined. Each run uncovered a new infrastructure bug (raw_response, model class, compaction, loop, event bridge), which was fixed and retried. This is a fire-fighting loop, not a systematic approach.
2. The fake test suite (S5-012) was built before the real failure mode was known. It models repeated llm_thinking but not the real model's DOM-exploration-then-text-only pattern, so it provided false confidence.
3. Sprint 5 success criteria assumed the real model would call plan_ready or ask_user given a reasonable prompt. This assumption was never tested with a fake adversarial model before the paid run. The fixture (ambiguous page with 3 Profile headings, no CTAs, user intent "Click Save") is genuinely hard for the model to resolve.
4. The E2E test acceptance criteria are ambiguous: the test waits for plan_ready or clarification, but PLANNING_NO_PROGRESS (the only terminal state reached) is not defined as acceptable. This is a spec gap, not just a code gap.

**Tickets contributing useful progress:** S5-001B, S5-002, S5-007, BUG-S5-013-004, BUG-S5-013-005, BUG-S5-013-006 (investigation).

**Tickets that missed key behavior:** S5-012 (fake suite does not model real failure mode); S5-015 (guardrails added but 14 tests still failing).

**Missing test layer:** Planner convergence contract — an adversarial fake model test that simulates the exact real LLM sequence and verifies the system behaves correctly.

---

## Section 5: Real Current Blocker

**The current blocker is planner convergence, not plumbing.**

Every infrastructure bug has been fixed. Evidence:
- Live model is reached on every run (llm_triggered=true in all 6 paid artifacts).
- Tool filtering works (15→6 confirmed in TOOL_FILTER logs).
- Telemetry attribution is complete (all 8 fields present in latest artifact).
- Guard fires at correct limit (PLANNING_NO_PROGRESS after 3 turns confirmed in latest log).
- Terminal event is surfaced to harness (observed_event_types=[runtime_rejected] confirmed in latest failure-context.json).

The remaining failure: the real model (gpt-4o-mini) given the ambiguous fixture ("Click Save" on a page with 3 Profile sections, no CTAs) calls llm_thinking, receives convergence pressure, calls llm_thinking again, receives pressure again, then fires the guard. It does not call ask_user or plan_ready within the 3-turn budget. The prompt pack says "call ask_user when ambiguous" but the model does not comply.

**What should NOT be touched next:** Additional paid runs before planner convergence contract tests are written and passing. No prompt rewrites as primary fix without evidence from fake adversarial tests first.

---

## Section 6: Missing Information / Observability Gaps

**Do we have actual model input payloads?**
No. The backend.log contains LLM_TELEMETRY line metadata (token counts, call IDs) but not the serialized message array sent to the model. We cannot inspect what the model received as the system prompt, skill text, or history on any given turn.

**Do we have assistant text for content-only turns?**
No. When the model produces output tokens without a tool call (observed in the BUG-S5-013-006 artifact: llm_004 produced 75 tokens of text), the text is not stored anywhere in the artifact. It is permanently lost. This is a first-class debugging gap.

**Do we know the exact tool schema the model saw?**
No. The TOOL_FILTER log records token counts and tool names but does not store the full generated tool schema text. We cannot verify whether ask_user and plan_ready appeared as unambiguous terminal options in the 584-token schema the model received.

**Observability gaps as first-class issues:**
1. No per-call payload file (redacted): system prompt + history + tool schema serialized as JSON, stored in artifact per call ID.
2. No assistant text capture for content-only responses: turns where the model produces text but no tool_calls must be logged and stored.
3. No tool schema snapshot: the generated tool schema text (6 tools × ~97 tokens average) should be stored once per run in the artifact.
4. No dynamic context capture: DYNAMIC_PLANNING_CONTEXT dynamic suffix fields (page_summary, queued_steps, validated_locators) are not logged. All were empty on the failing fixture, meaning the model had no pre-computed page anchor.

---

## Section 7: Required Before Next Paid E2E (Checklist)

- [ ] Redacted payload capture exists: each LLM call stores (redacted) system prompt, history, and tool schema in artifact as a per-call JSON file
- [ ] Adversarial fake convergence test exists: `test_step_plan_normalizer_convergence_contract_with_adversarial_fake_model` — fake sequence [llm_thinking, llm_thinking, llm_thinking] → assert PLANNING_NO_PROGRESS and runtime_rejected
- [ ] Content-only response test exists: `test_planning_guard_counts_content_only_response_as_non_terminal` — content-only (no tool_calls) LLM response is counted as non-terminal (verified by guard counter, not just turn limit)
- [ ] Tool schema clarity test exists: `test_tool_schema_text_makes_ask_user_and_plan_ready_clearly_terminal` — render 6 planning tools, assert ask_user and plan_ready descriptions unambiguously name them as terminal exits
- [ ] Ambiguous fixture expected behavior is defined: E2E test acceptance criteria must explicitly state whether PLANNING_NO_PROGRESS is a valid pass condition or whether ask_user is required — currently the test only accepts plan_ready/clarification but the real model never reaches either
- [ ] Broken assertion fixed: `test_repeated_llm_thinking_stops_before_harness_timeout` currently asserts `message_types.count("llm_thinking") == 2` but actual is 0 (guard intercepts before tool dispatch); must assert 0 or remove the assertion
- [ ] Internal one-call LLM probe decision made: should a single cheap internal probe call verify model will call ask_user on ambiguous fixture before running full E2E harness? Decision documented — not necessarily implemented.
- [ ] Paid E2E acceptance criteria clarified: define whether the test passes on (a) plan_ready, (b) ask_user/clarification, or (c) PLANNING_NO_PROGRESS-as-documented-terminal; currently only (a)/(b) accepted and (c) always occurs

---

## Section 8: Recommended Next Cluster

**Cluster name: Planner Convergence Contract and Observability**

This cluster must run entirely with fake LLM. No paid calls until all items are green.

**Work items:**

1. **Fix broken test assertion** in `tests/test_planning_through_controller_fake_model.py::test_repeated_llm_thinking_stops_before_harness_timeout` — change assertion from `llm_thinking count == 2` to `llm_thinking count == 0` (guard intercepts before tool dispatch). Cheap, correctness-critical, blocks accurate confidence signals.

2. **Write adversarial convergence contract test** — new file `tests/test_planning_convergence_contract.py`. Fake model sequence: [llm_thinking turn 1, llm_thinking turn 2, llm_thinking turn 3] → assert PLANNING_NO_PROGRESS fires, runtime_rejected emitted, no plan_ready/step_recorded/code_update/run_completed. Optionally extend to [llm_thinking, browser_get_state, dom_extract, text-only] to model the actual live sequence from BUG-S5-013-006.

3. **Write content-only response test** — fake model produces assistant message with text but no tool_calls. Assert planning guard counts this as non-terminal (planning_turns_without_terminal_output incremented). Confirm no false plan_ready event emitted.

4. **Write tool schema clarity test** — render the 6 planning-safe tools using the live tool_schema_policy pipeline. Assert the description text for ask_user includes "terminal" or "required when ambiguous". Assert plan_ready is not buried behind 7 undifferentiated enum values in send_to_overlay without a clear callout.

5. **Add payload capture to E2E artifact** — store per-call redacted JSON file (call_id, system prompt tokens + first 200 chars, history message count, full tool schema text) in artifact directory. This is required to debug any future paid failure without guessing.

6. **Clarify E2E acceptance criteria** — update `test_llm_required_ambiguous_action_flow.py` to explicitly define: if PLANNING_NO_PROGRESS fires on the ambiguous fixture, is that a pass (system correctly handled an unresolvable page) or a fail (model must call ask_user)? If ask_user is required, the prompt pack and tool schema must be strengthened first, and a fake test must prove the model would call it.

7. **Optional: single internal one-call LLM probe** — before the next full paid E2E run, run a single isolated LLM call with the exact step_plan_normalizer prompt + ambiguous fixture DOM result and check whether the model calls ask_user. Cost: <$0.01. This gives a signal about prompt/tool clarity without running the full harness.

---

## Section 9: Additional Gaps Found

**Stale / duplicated task files:**
- `.tasks-md/In Progress/SPRINT-004 Agent module extraction map.md` and `.tasks-md/In Progress/SPRINT-004 Full agent modularization.md` are deleted from In Progress but corresponding Done files exist. Git status shows these as D (deleted) with new versions as untracked (??) in Done. These should be committed or cleaned up — currently creating noise in `git status`.

**Broken test (currently failing, production relevance):**
- `tests/test_planning_through_controller_fake_model.py::test_repeated_llm_thinking_stops_before_harness_timeout` — assertion `llm_thinking count == 2` is wrong since commit be9d4c4 changed the guard to intercept before tool dispatch. This test has been wrong for multiple commits and was not caught because the overall test run shows it as 1 failure among 755 passes. It is providing false confidence about a critical safety contract.

**13 other currently failing tests (pre-existing, unrelated to S5-013 blocker):**
- `test_llm_planning_contracts.py` — 4 failures (intent_classifier, clarification_generator, journey_planner, plan_diff_editor contract tests)
- `test_llm_policy_gateway.py` — 2 failures (purpose-specific decision, tool restriction tests)
- `test_llm_specialist_contracts.py` — 7 failures (locator specialist, recovery diagnoser, budget guard, trace summarizer)
- These are not causing the S5-013 paid blocker but they mask regressions. They should be triaged before any claim that the suite is green.

**E2E test acceptance criteria gap:**
- `test_llm_required_ambiguous_action_flow` waits for plan_ready or clarification (line 58: `_wait_for_plan_or_clarification`) and has no branch for PLANNING_NO_PROGRESS as a valid outcome. Yet PLANNING_NO_PROGRESS is the only terminal state reached in all Sprint 5 paid runs on this fixture. The test is structurally unable to pass on the current ambiguous fixture without either (a) the model calling ask_user, or (b) the test accepting no-progress as valid. This is a spec ambiguity that was not resolved before paid runs.

**Missing artifacts — no events.ndjson:**
- The latest artifact directory does not contain an events.ndjson file. The artifact has backend.log, token-report.json, failure-context.json, summary.md, but no structured event stream file. This limits programmatic analysis of event sequences.

**Dynamic context empty on ambiguous fixture:**
- DYNAMIC_PLANNING_CONTEXT dynamic suffix had all fields empty (page_summary, queued_steps, validated_locators) on the failing fixture runs. The model received no pre-computed page anchor and had to call DOM tools to understand the page. This is a design gap: if the harness loads a page, it should pre-populate page_summary before calling the planner. Without this, the model's DOM exploration is predictable and expected.

**Token reduction not achieved on live path:**
- The S5-013 acceptance criterion stated token reduction ≤110% of baseline. The latest artifact shows 8136 total estimated input tokens across 3 calls vs a single-call baseline of 4442 — this is 183% of baseline because the model makes 3 calls before no-progress. Per-call input tokens (2636, 2712, 2788) are individually well below baseline, but convergence failure means token cost multiplies per turn. Token efficiency requires convergence, not just per-call optimization.

**Prompt cache hit rate is 0:**
- All paid runs show cached_tokens=0 despite S5-014 stable prefix strategy. The stable prefix hash is consistent (prefix_hash=45ae641d9c816ac8 across all 3 calls in latest run) but no cache hits occur. This may be because the OpenAI prompt cache requires a minimum prefix length or minimum reuse interval that is not being met on short test runs. This should be investigated separately.
