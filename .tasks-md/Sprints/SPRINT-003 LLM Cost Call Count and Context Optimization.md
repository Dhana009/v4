# SPRINT-003 LLM Cost, Call Count, and Context Optimization

Status: In Progress (Phase 2)
Sprint: Sprint 3
Duration: Bi-weekly
Primary focus: Complete LLM Mode cost reduction and context control
Priority: P0

## Sprint goal

Reduce LLM cost and make LLM Mode scalable before adding more broad product features.

Sprint 3 focuses on both:

1. Reducing the number of LLM calls per flow.
2. Reducing input tokens per LLM call.

## Why this sprint exists

Recent usage evidence showed high input-token usage during repeated E2E/regression runs.

Observed concerns:

- repeated large system/skill prompts
- simple flows making multiple LLM calls
- full or broad skill content included when compact context should be enough
- need for local telemetry instead of relying only on OpenAI dashboard
- need to measure before and after optimization

## Source rules

- PRD v2.3 Complete LLM Mode
- Complete LLM Mode Runtime Policy Spec
- Complete LLM Mode P0 Scenario Spec
- Token efficiency rule: deterministic backend/DOM first; LLM only when required
- Context policy: never send raw full DOM or full history by default
- Skill policy: compact core always, summaries by purpose, full skills only on escalation
- Backend truth rule: LLM proposes; backend validates and owns truth

## Selected Sprint 3 stories

Core Sprint 3:

1. INT-OBS-001 LLM call and token telemetry report
2. INT-LLM-002 Compact system prompt and skill summaries
3. INT-CALL-001 Deterministic fast path for simple picked-element actions
4. INT-CTX-001 Context budget gate and history compaction
5. INT-DOM-002 Compact page and section intelligence packet
6. INT-E2E-002 Token-budget regression checks

Stretch only:

7. INT-LLM-003 Route step_plan_normalizer through LLMRuntimeController

## Execution order

1. INT-OBS-001 — measure call count and token usage first
2. INT-LLM-002 — reduce repeated system/skill prompt size
3. INT-CALL-001 — reduce LLM calls for simple deterministic flows
4. INT-CTX-001 — cap/summarize history and DOM/tool outputs
5. INT-DOM-002 — provide compact page intelligence instead of raw DOM
6. INT-E2E-002 — add regression-level token budget checks
7. INT-LLM-003 — stretch only after the above are stable

## Success criteria

Sprint 3 is successful only if:

- existing 5 E2E tests still pass
- LLM call count is visible per test/run
- total estimated input tokens are visible per test/run
- largest prompt is visible
- system/skill token contribution is visible
- DOM/history token contribution is visible
- simple picked-element flows reduce LLM call count
- simple flows reduce system/skill prompt tokens by at least 50%
- average input tokens per simple E2E flow reduce by at least 30–50%
- no raw DOM/full history is resent by default
- backend still owns runtime truth
- no confirmation/execution safety gate is removed

## Explicit non-goals

Do not implement in Sprint 3 unless explicitly approved:

- full multi-model routing
- cheap/nano model production split
- full Trace UI redesign
- frontend tab rename/redesign
- docked/devtools-style frontend layout
- replay repair/versioning
- permission/autonomy mode
- broad product feature expansion

## Baseline (before Sprint 3 optimization — Sprint 2 final state)

Captured from: Sprint 2 commit 5a43872 / pre-Sprint 3 E2E runs (basic_click_flow-20260508-165332)
Note: Sprint 3 telemetry breakdown fields (skill_tokens etc.) were not emitted pre-Sprint 3.
Baseline token counts are confirmed identical to Sprint 3 runs — same LLM call patterns.

| Test | calls | total input tokens | largest call | skill_tokens | system_tokens |
|---|---|---|---|---|---|
| basic_click_flow | 5 | ~22,121 | 5,610 | (not tracked) | (not tracked) |
| exact_text_assertion_flow | 6 | ~27,337 | 5,927 | (not tracked) | (not tracked) |
| visible_assertion_flow | 6 | ~27,841 | 5,943 | (not tracked) | (not tracked) |
| correction_assert_then_click | 8 | ~42,603 | 7,550 | (not tracked) | (not tracked) |
| mvp_001_lifecycle_smoke | 5 | ~22,665 | 5,646 | (not tracked) | (not tracked) |

5 E2E result before Sprint 3: all 5 pass (Sprint 2 evidence: commit 5a43872)

## Sprint 3 E2E verification — 2026-05-08

All 5 E2E tests pass. Token breakdown now visible per call.

E2E run artifacts: test-results/autoworkbench-e2e/ (Sprint 3 runs, 2026-05-08 ~12:12-12:15 UTC)

Note: first run had 2 OpenAI latency flakes (6s/call vs normal 1-2s/call — same token counts,
same code path). Rerun confirmed both pass. Not a Sprint 3 regression.

### Sprint 3 token report (per test, passing runs)

**basic_click_flow** (artifact: basic_click_flow-20260508-174444)
- calls: 6
- total estimated input tokens: 27,332
- largest call: llm_006 = 5,666 tokens
- system_prompt_tokens per call: 3,182 (calls 1-5), 3,302 (call 6)
- skill_tokens per call: 3,135 (all calls)
- tool_schema_tokens: 584 (calls 1-5), 1,458 (call 6)
- message_history_tokens peak: 422
- dom_or_tool_result_tokens peak: 404

**exact_text_assertion_flow** (artifact: exact_text_assertion_flow-20260508-174501)
- calls: 6
- total estimated input tokens: 27,337
- largest call: llm_006 = 5,927 tokens
- system_prompt_tokens: 2,853 (calls 1-5), 3,013 (call 6)
- skill_tokens: 2,805 (all calls)
- tool_schema_tokens: 584 (calls 1-5), 1,458 (call 6)
- dom_or_tool_result_tokens peak: 888 (DOM extract result)

**visible_assertion_flow** (artifact: visible_assertion_flow-20260508-174254)
- calls: 6
- total estimated input tokens: 27,841
- largest call: llm_006 = 5,943 tokens
- system_prompt_tokens: 2,853 (calls 1-5), 2,978 (call 6)
- skill_tokens: 2,805 (all calls)
- dom_or_tool_result_tokens peak: 883

**correction_assert_then_click** (artifact: correction_assert_then_click_flow-20260508-174313)
- calls: 8 (includes plan_diff_editor correction round-trip)
- total estimated input tokens: 42,603
- largest call: llm_008 = 7,550 tokens
- skill_tokens: 3,135 (all calls)
- message_history_tokens peak: 2,238 (after correction history builds up)

**mvp_001_lifecycle_smoke** (artifact: mvp_001_lifecycle_smoke-20260508-174337)
- calls: 5
- total estimated input tokens: 22,665
- largest call: llm_005 = 5,646 tokens
- skill_tokens: 3,135 (all calls)

### Key findings

1. Token breakdown is now fully visible per call — INT-OBS-001 confirmed working.
2. skill_tokens = 2,805–3,135 per call — dominant cost source (system prompt + skills).
3. dom_or_tool_result_tokens: up to 888 tokens per call from DOM extract results.
4. Context budget gate (INT-CTX-001) active: budget_status=ok on all Sprint 3 runs
   (no tool result exceeded 800 token cap in these simple flows).
5. Fast path (INT-CALL-001): not triggered in E2E tests — these tests use full LLM path
   because picked element data arrives via WebSocket picker, not inline locator pre-validation.
6. Skill loading (INT-LLM-002): skill_policy.py active; COMPACT_ONLY_PURPOSES enforced.
7. Page intelligence (INT-DOM-002): module available; not yet called from main agent path
   (INT-DOM-002 is infrastructure — integration wiring is Sprint 4 scope).
8. Token report (INT-E2E-002): token_report.py available for harness integration;
   LLM_TELEMETRY lines now carry full breakdown for aggregation.

### Quality result

- basic_click: PASS
- exact_text_assertion: PASS
- visible_assertion: PASS
- correction_assert_then_click: PASS
- mvp_001_lifecycle_smoke: PASS
- unit/contract (470 tests): PASS
- no tests weakened, skipped, or xfailed

## Acceptance correction — Sprint 3 Phase 2

Sprint 3 Phase 1 produced infrastructure and measurement. Phase 1 is complete for:

- INT-OBS-001: Done — token breakdown visible in live E2E telemetry
- INT-E2E-002: Testing — parser module exists but token-report.json never written to artifact dir

The following stories are NOT done because they have no proven live E2E impact:

- INT-LLM-002: Testing — skill_tokens still 2,805–3,135/call in live E2E path
- INT-CALL-001: Testing — fast path module exists but never triggered in WebSocket picker flow
- INT-CTX-001: Testing — budget gate exists but budget_status=ok, no capping in live E2E flows
- INT-DOM-002: Testing — page intelligence module exists but not wired into live agent path

Phase 2 goal: wire all four modules into the live product path and prove token reduction.

Required measurable outcomes before Sprint 3 can be accepted as Done:

| Test | Baseline calls | Baseline input tokens | Target calls | Target tokens |
|---|---|---|---|---|
| basic_click_flow | 6 | 27,332 | ≤3 | materially lower |
| exact_text_assertion_flow | 6 | 27,337 | ≤3 | materially lower |
| visible_assertion_flow | 6 | 27,841 | ≤3 | materially lower |
| correction_assert_then_click | 8 | 42,603 | reduce if safe | no quality loss |

All 5 E2E tests must still pass after Phase 2 wiring.

## Dependency rules

- INT-OBS-001 must complete before INT-E2E-002.
- INT-OBS-001 should run before optimization work so we can measure baseline.
- INT-LLM-002 and INT-CTX-001 must prove token reduction using INT-OBS-001 telemetry.
- INT-CALL-001 must prove call-count reduction using INT-OBS-001 telemetry.
- Quality gates must run after every optimization story.

## Sprint 3 principle

Every LLM call must justify itself.
Every token must have a reason.
If deterministic backend/DOM can do it safely, no LLM call.
If LLM is needed, send the smallest purpose-specific context.
