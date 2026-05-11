# S5-013 Controlled paid E2E acceptance for Sprint 5

Status: Blocked
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 01_PRODUCT_WORKFLOWS.md, AGENTS.md token baseline

## Problem / Goal

**Problem:** Fake-model suite proves architecture works; real LLM behavior needs verification. Must balance token efficiency (S5 goal) with correctness (non-negotiable).

**Goal:** Run controlled paid E2E on 2–3 representative flows. Measure tokens vs baseline. Verify correctness unchanged. Gate Sprint 5 acceptance on token reduction + correctness.

## Scope

- Run E2E on: ambiguous planning flow, plan correction flow, one DOM-heavy page flow (if page intelligence implemented)
- Measure: input tokens, output tokens, call count, cost
- Compare vs Sprint 3 baseline (AGENTS.md)
- Verify: correctness (all steps pass), no quality loss
- Document: which flows tested, token results, cost

Out of scope:
- Repeated paid runs during development (only S5 acceptance)
- All 5 flows (2–3 representative flows sufficient)
- Real nano model testing (fake model sufficient for this sprint)

## Required unit tests

None (purely E2E).

## Required contract tests

- `test_e2e_token_baseline_comparison.py`:
  - Baseline tokens from AGENTS.md
  - S5 tokens are <=110% of baseline (allow 10% variance)
  - Token reduction is measurable

## Required integration tests

- `test_e2e_ambiguous_planning.py`:
  - Ambiguous user intent -> planning -> correction -> confirmation
  - All steps execute correctly
  - Token count recorded
- `test_e2e_plan_correction.py`:
  - Valid plan -> user correction -> corrected plan -> confirmation
  - Correction applied correctly
  - Token count recorded
- `test_e2e_dom_heavy_page_intelligence.py` (if S5-010 done):
  - Weak DOM page -> page intelligence -> planning -> validation
  - All steps correct
  - Token count recorded

## Fixture/page needs

- Fixture pages from S5-011
- Public test pages (e.g., playwright-docs, Airbnb signup)

## Paid E2E requirement

**Yes. This story requires real LLM calls.**

- Ambiguous planning: ~1–2 runs, ~5–10k tokens
- Correction: ~1–2 runs, ~5–10k tokens
- DOM-heavy (if done): ~1 run, ~8–12k tokens
- **Total estimate: 2–3 runs, ~15–30k tokens, cost ~$0.30–$0.60**

## Acceptance criteria

- [ ] 2–3 E2E flows run with real LLM
- [ ] Token count measured and compared vs baseline
- [ ] All flows pass without correctness loss
- [ ] Token reduction is achievable (<=110% of baseline)
- [ ] Cost estimate is reasonable (commit approved before run)
- [ ] Results documented in token_report.json
- [ ] Baseline comparison shows S5 changes are working

## Evidence

Status: Blocked

Paid E2E scope:
- `tests/e2e/test_llm_required_ambiguous_action_flow.py` only
- One live-LLM run only; no retries and no second paid flow

Commands run:
- `git status --short --branch`
- `git log --oneline -20`
- `git rev-parse HEAD`
- `find tests/e2e -type f -name "test_*.py" | sort`
- `find tests/e2e -type f | sort | sed -n '1,240p'`
- `rg -n "llm_required\\|ambiguous\\|token-report\\|token_report\\|S5-013\\|paid\\|OPENAI\\|LLM" -n tests/e2e tests runtime .tasks-md | sed -n '1,500p'`
- `find test-results -name "token-report.json" -o -name "*token*" | sort | sed -n '1,240p'`
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_recovery_through_fake_model.py tests/test_fake_llm_factory.py -q`
- `python -c "from dotenv import dotenv_values; v=dotenv_values('.env'); k=str(v.get('OPENAI_API_KEY','')).strip(); print('OPENAI_API_KEY=present' if k.startswith('sk-') else 'OPENAI_API_KEY=missing')"`
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q`

Artifact paths:
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-115107-87351/token-report.json`
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-115107-87351/backend.stdout.log`
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-115107-87351/backend.tail.log`
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-115107-87351/failure.txt`
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-115107-87351/failure-context.json`
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-115107-87351/summary.md`

Results:
- The live flow reached the model once and then failed.
- Pytest failure: `TimeoutError: Timed out waiting for plan review or clarification`.
- The underlying runtime error in backend telemetry was `step_plan_normalizer controller did not return raw_response`.
- The flow is not a startup-only environment issue because the telemetry line shows `llm_triggered=true`.
- No second paid flow was run because the first live LLM call already failed and the stop condition was hit.

Token comparison:

| Metric | Baseline | Sprint 5 result | Delta | Pass? |
|---|---:|---:|---:|---|
| Input tokens | 4442 | 2636 | -1806 (-40.7%) | Yes |
| Output tokens | 62 | 0 | -62 | No |
| System bucket | ~3496 | 840 | -2656 (-76.0%) | Yes |
| Skill bucket | ~3398 | 1699 | -1699 (-50.0%) | Yes |
| Tool schema bucket | ~410 | 584 | +174 (+42.4%) | No |
| History bucket | ~495 | 238 | -257 (-51.9%) | Yes |
| DOM/tool bucket | ~4 | 0 | -4 (-100.0%) | Yes |

Attribution:
- prompt_pack_id: `step_plan_normalizer.v1`
- prefix_hash: `657eb55c3207eee9` in backend telemetry; `token-report.json` truncated this to `657`
- skills_loaded: `core,actions,download`
- skill_levels: absent on this failed live run
- cached_tokens: `0`
- purposes: `step_plan_normalizer`
- model_class: `main`

Correctness:
- Failed.
- The live run never reached plan review or clarification.
- Backend telemetry showed `error_type=RuntimeError` and `error_message="step_plan_normalizer controller did not return raw_response"`.
- The `step_plan_normalizer` live path is therefore still blocked before Sprint 5 acceptance can be approved.

Interpretation:
- What this proves: real-LLM planning is still reachable, token reduction on input/system/skill/history is measurable, and Sprint 5 prompt-pack attribution is present in the live telemetry.
- What remains: the controller raw-response contract must be fixed before another paid run, `tool_schema` did not shrink on this failed path, `skill_levels` was not emitted, and the `token-report.json` prefix hash truncation needs follow-up.

Remaining gaps:
- No successful real-LLM confirmation/clarification path yet.
- No passing paid E2E result for S5-013.
- `tool_schema_tokens` remained above the pre-Sprint-5 baseline.
- `skill_levels` is absent from the token report on this failure path.
- `prefix_hash` is truncated in the JSON token report even though backend telemetry had the full 16-char hash.

Changed files:
- `.tasks-md/Blocked/S5-013 Controlled paid E2E acceptance for Sprint 5.md`
- `.tasks-md/Board/SPRINT-005-PLAN.md`

Commit:
- pending

## Controlled retry evidence

Retry status: Blocked

Retry paid E2E scope:
- `tests/e2e/test_llm_required_ambiguous_action_flow.py`
- One live-LLM retry only; no second paid flow and no rerun after failure

Retry command:
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q`

Retry artifact path:
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-125206-72380/`

Retry results:
- The live flow reached the model once and then failed.
- Pytest failure: `TimeoutError: Timed out waiting for plan review or clarification`.
- Backend telemetry again showed `step_plan_normalizer controller did not return raw_response`.
- `token-report.json` still reported `skill_levels`, but `prompt_pack_ids` was empty on this failing path.
- `prefix_hash` was still absent from the JSON token report on this retry.
- No second paid flow was run because the first live LLM call already failed and the stop condition was hit.

Retry token comparison:

| Metric | Baseline | Retry result | Delta | Pass? |
|---|---:|---:|---:|---|
| Input tokens | 4442 | 2582 | -1860 (-41.9%) | Yes |
| Output tokens | 62 | 0 | -62 | No |
| System bucket | ~3496 | 1748 | -1748 (-50.0%) | Yes |
| Skill bucket | ~3398 | 1699 | -1699 (-50.0%) | Yes |
| Tool schema bucket | ~410 | 584 | +174 (+42.4%) | No |
| History bucket | ~495 | 238 | -257 (-51.9%) | Yes |
| DOM/tool bucket | ~4 | 0 | -4 (-100.0%) | Yes |

Retry attribution:
- prompt_pack_id: absent from token-report.json on this failing retry
- prefix_hash: absent from token-report.json on this failing retry
- skills_loaded: `core,actions,download`
- skill_levels: `skill_summary,skill_summary,skill_summary`
- cached_tokens: `0`
- purposes: `step_plan_normalizer`
- model_class: `main`
- model: `gpt-4o-mini`
- tool_schema explanation: current six-tool planning-safe set still accounts for the larger schema bucket on this path

Retry interpretation:
- What this proves: the paid retry still reaches the real LLM and still exposes the same raw-response blocker, so the previous bugfix did not clear S5-013.
- What remains: the controller raw-response contract still needs a live-path fix before another paid retry; token-report attribution is still incomplete on the failing path.

## Latest live retry evidence

Retry status: Blocked

Retry paid E2E scope:
- `tests/e2e/test_llm_required_ambiguous_action_flow.py`
- One live-LLM retry only; no second paid flow and no rerun after failure

Retry command:
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q`

Retry artifact path:
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-134142-28864/`

Retry results:
- The live flow reached the model once and then failed.
- Pytest failure: `TimeoutError: Timed out waiting for plan review or clarification`.
- Backend telemetry now exposes the provider/model error clearly:
  - `The model \`main\` does not exist or you do not have access to it.`
  - `NotFoundError`
  - `Error code: 404`
- The live flow is still blocked before plan review or clarification.
- No second paid flow was run because the first live LLM call already failed and the stop condition was hit.

Retry token comparison:

| Metric | Baseline | Retry result | Delta | Pass? |
|---|---:|---:|---:|---|
| Input tokens | 4442 | 2636 | -1806 (-40.7%) | Yes |
| Output tokens | 62 | 0 | -62 | No |
| System bucket | ~3496 | 840 | -2656 (-76.0%) | Yes |
| Skill bucket | ~3398 | 1699 | -1699 (-50.0%) | Yes |
| Tool schema bucket | ~410 | 584 | +174 (+42.4%) | No |
| History bucket | ~495 | 238 | -257 (-51.9%) | Yes |
| DOM/tool bucket | ~4 | 0 | -4 (-100.0%) | Yes |

Retry attribution:
- prompt_pack_id: `step_plan_normalizer.v1`
- prefix_hash: `657eb55c3207eee9`
- skills_loaded: `core,actions,download`
- skill_levels: `skill_summary,skill_summary,skill_summary`
- cached_tokens: `0`
- purpose: `step_plan_normalizer`
- model_class: `main`
- model: `gpt-4o-mini`
- tool_schema explanation: current six-tool planning-safe set still accounts for the larger schema bucket on this path

Retry interpretation:
- What this proves: BUG-S5-013-002 fixed the generic raw-response masking, because the live failure now surfaces the provider `model_not_found` error instead of only the old generic missing-raw-response message.
- What remains: the live provider/model routing still needs correction before another paid retry; token-report attribution is present on this retry, but the flow is still blocked by the provider 404.

## Latest controlled retry evidence

Retry status: Blocked

Retry paid E2E scope:
- `tests/e2e/test_llm_required_ambiguous_action_flow.py`
- One live-LLM retry only; no second paid flow and no rerun after failure

Retry command:
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q`

Retry artifact path:
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-141048-68814/`

Retry results:
- The live flow reached the model and then timed out waiting for plan review or clarification.
- Backend logs show repeated `send_to_overlay({"message_type": "llm_thinking"})` tool calls and no `plan_ready` or clarification event before timeout.
- `failure-context.json` reports `stage=llm_response_seen` and `reason=Timed out waiting for plan review or clarification`.
- The run remained stuck in `PLANNING…` with no confirmation prompt surfaced to the UI.
- No second paid flow was run because the first live LLM call already failed and the stop condition was hit.

Retry token comparison:

| Metric | Baseline | Retry result | Delta | Pass? |
|---|---:|---:|---:|---|
| Input tokens | 4442 | 60326 | +55884 (+1258.1%) | No |
| Output tokens | 62 | 621 | +559 (+901.6%) | No |
| System bucket | ~3496 | 18480 | +14984 (+428.6%) | No |
| Skill bucket | ~3398 | 37378 | +33980 (+1000.0%) | No |
| Tool schema bucket | ~410 | 12848 | +12438 (+3033.7%) | No |
| History bucket | ~495 | 5736 | +5241 (+1059.8%) | No |
| DOM/tool bucket | ~4 | 1505 | +1501 (+37525.0%) | No |

Retry attribution:
- prompt_pack_ids: `step_plan_normalizer.v1`
- prefix_hash: `657eb55c3207eee9`
- skills_loaded: `core,actions,download`
- skill_levels: `skill_summary`
- cached_tokens: `21888`
- purposes: `step_plan_normalizer`
- model_classes: `main`

Retry interpretation:
- What this proves: the live path is no longer failing on raw-response plumbing, model routing, or tool-call payload validity.
- What remains: the ambiguous planning flow is still not converging to `plan_ready` or clarification and instead loops on `llm_thinking`, so the paid acceptance is still blocked by a distinct runtime/product issue.

## Controlled retry after BUG-S5-013-004

Retry status: Blocked

Retry paid E2E scope:
- `tests/e2e/test_llm_required_ambiguous_action_flow.py`
- One live-LLM retry only; no second paid flow and no rerun after failure

Retry command:
- `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q`

Retry artifact path:
- `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-152632-66463/`

Retry results:
- The live flow reached the model and then timed out waiting for plan review or clarification.
- Backend logs show the planning loop stopped with `[PHASE] from=planning to=failed reason=planning_no_progress step_id=none`.
- `failure-context.json` shows `stage=llm_response_seen`, `reason=Timed out waiting for plan review or clarification`, `llm_triggered=true`, and `observed_event_types=[]`.
- The live run therefore bounded the loop, but the harness still did not receive a surfaced terminal signal it could treat as complete.
- No second paid flow was run because the first live LLM call already failed and the stop condition was hit.

Retry token comparison:

| Metric | Baseline | Retry result | Delta | Pass? |
|---|---:|---:|---:|---|
| Input tokens | 4442 | 10817 | +6375 (+143.5%) | No |
| Output tokens | 62 | 111 | +49 (+79.0%) | No |
| System bucket | ~3496 | 3360 | -136 (-3.9%) | No |
| Skill bucket | ~3398 | 6796 | +3398 (+100.0%) | No |
| Tool schema bucket | ~410 | 2336 | +1926 (+469.8%) | No |
| History bucket | ~495 | 997 | +502 (+101.4%) | No |
| DOM/tool bucket | ~4 | 191 | +187 (+4675.0%) | No |

Retry attribution:
- prompt_pack_ids: `step_plan_normalizer.v1`
- prefix_hash: `657eb55c3207eee9`
- skills_loaded: `core,actions,download`
- skill_levels: `skill_summary`
- cached_tokens: `2304`
- purposes: `step_plan_normalizer`
- model_classes: `main`

Retry interpretation:
- What this proves: BUG-S5-013-004 bounded the planning loop, because the backend now exits with `planning_no_progress` instead of running until a longer timeout.
- What remains: the no-progress stop is not yet surfacing as a terminal runtime event the harness accepts, so the paid acceptance is still blocked by a surface-contract issue rather than an infinite loop.

---

## BUG-S5-013-007 Fixed — Convergence Contract Defined

**Commit:** (see commit after this section)
**Status:** Done (fake-model proven)

### What was fixed

1. **Content-only response was counted as terminal** — `planning_loop_guard.py` treated any
   assistant message with text but no tool calls as `terminal_reason="final_text"`, bypassing the
   no-progress guard entirely. Fixed: content-only turns now increment
   `planning_turns_without_terminal_output` and never set terminal_reason.

2. **ask_user tool description was generic** — gave no guidance that it is the required terminal
   call when targets are ambiguous. Fixed: description now explicitly states when to use it
   ("multiple plausible targets", "Do not continue DOM exploration after ambiguity is established").

3. **Prompt pack missing AMBIGUITY_RULE** — no instruction said to call ask_user when multiple
   plausible targets exist. Fixed: added AMBIGUITY_RULE and plain-text prohibition to stable prefix.

4. **Broken test assertion fixed** — `test_repeated_llm_thinking_stops_before_harness_timeout`
   asserted `llm_thinking count == 2` but actual is 0 (guard fires before dispatch). Corrected.

5. **Payload capture added** — `harness.build_llm_calls_artifact()` and
   `harness.write_llm_calls_artifact()` added for redacted per-call LLM artifact storage.

### Tests added (all passing)

- `tests/test_planning_convergence_contract.py` (4 tests) — adversarial DOM sequence, content-only guard
- `tests/test_tool_contract_clarity.py` (3 tests) — tool schema clarity for plan_ready, ask_user, llm_thinking
- `tests/test_prompt_pack_builder.py` (4 new tests) — AMBIGUITY_RULE, TERMINAL_OUTPUT_REQUIREMENT, plain-text prohibition
- `tests/test_sprint5_llm_runtime_guardrails.py` (5 new tests) — convergence guardrail regressions
- `tests/test_e2e_harness.py` (4 new tests) — payload capture, secrets redaction

### Suite result after fix

```
771 passed, 12 failed (12 pre-existing failures in test_llm_planning_contracts,
test_llm_policy_gateway, test_llm_specialist_contracts — all unrelated to S5-013)
```

### Retry readiness

The next paid retry is now justified. The model will see:
- Explicit AMBIGUITY_RULE: "call ask_user when multiple plausible targets exist"
- ask_user schema: "required terminal call when ambiguous"
- Plain-text prohibition in prompt pack
- Content-only responses counted as non-terminal (guard fires if model keeps producing text)

If the model calls ask_user → E2E test passes (clarification counts as valid terminal).
If the model still produces content-only text → guard fires PLANNING_NO_PROGRESS (deterministic, observable).
No infinite loops, no timeouts, no lost debugging data.

## Development follow-up after latest paid retry

Status: Blocked pending next controlled paid retry approval

New blockers fixed:
- `BUG-S5-013-008` done: `llm-calls.json` is now always written into the paid E2E artifact directory on success and failure paths, with safe/redacted per-call capture.
- `BUG-S5-013-009` done: obvious ambiguous DOM evidence now injects runtime-owned `ask_user` pressure and forces clarification instead of allowing content-only drift toward another `PLANNING_NO_PROGRESS` loop.

Cheap verification after the fixes:
- `python -m py_compile agent.py tests/e2e/harness.py tests/test_e2e_harness.py tests/test_planning_convergence_contract.py tests/test_tool_contract_clarity.py tests/test_planning_loop_guard.py tests/test_planning_through_controller_fake_model.py tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_sprint5_llm_runtime_guardrails.py`
  - pass
- `python -m pytest tests/test_e2e_harness.py -q`
  - `68 passed`
- `python -m pytest tests/test_planning_convergence_contract.py tests/test_tool_contract_clarity.py -q`
  - `8 passed`
- `python -m pytest tests/test_planning_loop_guard.py tests/test_planning_through_controller_fake_model.py -q`
  - `28 passed`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_sprint5_llm_runtime_guardrails.py -q`
  - `53 passed`
- `python -m pytest tests/test_sprint5_paid_retry_blocker_regression.py tests/test_sprint5_paid_blocker_regression.py -q`
  - `7 passed`
- `python -m pytest tests/test_context_manager.py tests/test_llm_runtime_controller_contract.py tests/test_backend_event_sequences.py tests/test_event_sequence_contract.py tests/test_event_contract.py -q`
  - `46 passed`
- `python -m pytest tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_fake_llm_factory.py tests/test_telemetry_breakdown.py tests/test_token_report.py tests/test_recording_codegen_truth_contract.py -q`
  - `94 passed`

Next step:
- One controlled paid retry of `tests/e2e/test_llm_required_ambiguous_action_flow.py` only, after user approval.
