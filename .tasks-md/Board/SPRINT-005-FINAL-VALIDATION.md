# SPRINT-005 Final Validation Report

**Generated:** 2026-05-12
**HEAD at validation:** 225af3c (Sprint 5 implementation tip)
**Branch:** main (31 commits ahead of origin/main)
**Outcome:** All phases green. Sprint 5 closure recommended.

---

## 1. Story status (15/15 Done)

| ID | Title | Status |
|----|-------|--------|
| S5-001 | Live LLM call path through LLMRuntimeController | Done |
| S5-001B | Controller raw-response tool-call preserving planning path | Done |
| S5-002 | Purpose-specific prompt pack builder | Done |
| S5-003 | Skill summary/full-skill escalation policy | Done |
| S5-004 | Tool schema filtering by purpose | Done |
| S5-005 | Context reuse and delta context for correction | Done |
| S5-006 | Recovery-specific prompt context | Done |
| S5-007 | Token report attribution upgrade | Done |
| S5-008 | ModelRouter real cheap/main routing contract | Done |
| S5-009 | Page Intelligence LLM route design and contract | Done |
| S5-010 | Page Intelligence first fake-model integration | Done |
| S5-011 | DOM-heavy fixture pages for LLM-runtime testing | Done |
| S5-012 | Fake-model integration suite | Done |
| S5-013 | Controlled paid E2E acceptance | Done |
| S5-014 | Prompt cache-friendly stable prefix strategy | Done |
| S5-015 | Sprint 5 regression guardrails | Done |

No story in Planning / In Progress / Blocked.

## 2. Bugs (all Done)

BUG-S5-013-001 through BUG-S5-013-012 — all closed (13 total, S5-013-003 has two entries with same ID prefix).

No BUG-S5-FINAL-* required: no validation regression found.

## 3. Cheap tests run

| Suite | Result |
|-------|--------|
| `test_model_router.py` + `test_page_intelligence_schema.py` + `test_page_intelligence_fake_integration.py` + `test_dom_heavy_fixtures.py` + `test_prompt_pack_builder.py` + `test_prompt_pack_safety_rules.py` + `test_sprint5_llm_runtime_guardrails.py` + `test_tool_policy_contract.py` + `test_tool_schema_filter.py` + `test_llm_runtime_controller_contract.py` + `test_planning_convergence_contract.py` + `test_tool_contract_clarity.py` + `test_planning_loop_guard.py` + `test_planning_through_controller_fake_model.py` + `test_real_llm_planner_contract.py` + `test_fake_llm_factory.py` + `test_telemetry_breakdown.py` + `test_token_report.py` | **249 passed, 1 skipped** (skipped: real LLM contract — env-gated) |
| `test_context_manager.py` + `test_backend_event_sequences.py` + `test_event_sequence_contract.py` + `test_event_contract.py` + `test_recording_codegen_truth_contract.py` + `test_e2e_harness.py` + `test_sprint5_paid_blocker_regression.py` + `test_sprint5_paid_retry_blocker_regression.py` | **116 passed** |

**Total cheap: 365 passed, 1 skipped.**

## 4. Broader pytest scan

Skipped: `pytest --markers` shows no `paid` / `live` / `e2e` markers configured. No safe broad command without risk of triggering paid runs implicitly. Targeted suites above already cover Sprint 5 surface.

## 5. Real LLM contract probe (Phase 3)

- Command: `RUN_PAID_LLM_CONTRACT=1 python -m pytest tests/test_real_llm_planner_contract.py -q`
- Result: **1 passed in 3.14s**
- Outcome: ambiguous Profile prompt → real `gpt-4o-mini` returned `ask_user` schema-shaped output. No browser, no Playwright. Confirms prompt contract still drives real model to terminal output.

## 6. Paid E2E (Phase 4)

- Command: `python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q`
- Result: **1 passed in 11.23s**
- Artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260512-192657-45848/`
- Terminal output: `ask_user(question="Could you clarify which element you intend to save? Is it a form, a document, or something else?")`
- No `PLANNING_NO_PROGRESS`, no `THINKING_NOT_ALLOWED_AFTER_CONVERGENCE_NARROWING`, no provider/tool-chain error.
- Backend log shows full convergence path:
  1. `[MODEL_ROUTER] purpose=step_plan_normalizer model=gpt-4o-mini`
  2. `llm_001` → `send_to_overlay(message_type=llm_thinking)`
  3. `[AGENT] planning convergence pressure: injected after llm_thinking turn`
  4. `[AGENT] step_plan_normalizer: tool surface narrowed to ask_user+send_to_overlay`
  5. `[AGENT] step_plan_normalizer: forcing tool_choice=ask_user`
  6. `llm_002` → `ask_user` (finish_reason=stop)

## 7. Token summary (latest paid E2E)

| Metric | Value |
|--------|-------|
| call_count | 2 |
| total_estimated_input_tokens | 5026 |
| total_output_tokens | 45 |
| largest_call_id | llm_001 |
| largest_call_tokens | 2636 |
| top_token_source | skill |
| breakdown.system | 2105 |
| breakdown.skill | 3398 |
| breakdown.tool_schema | 846 |
| breakdown.history | 552 |
| breakdown.dom_tool_result | 0 |
| skills_loaded | core, actions, download |
| skill_levels | skill_summary |
| prompt_pack_ids | step_plan_normalizer.v1 |
| model_classes | main |

## 8. Fixes made during validation

None. No regression detected.

## 9. Remaining risks

- Skill bucket (3398) still dominates token cost. Within Sprint 5 acceptance bounds; further compression deferred.
- `tool_schema` bucket 846 tokens on llm_001 (full 6-tool surface) but narrows to 2-tool ≤300 tokens on llm_002.
- `gpt-4o-mini` still emits `llm_thinking` on first turn. Defense-in-depth (schema strip + forced tool_choice + convergence pressure) keeps terminal output deterministic.

## 10. Deferred (not Sprint 5 blockers)

- Page Intelligence schema/helper not auto-invoked by `agent.py` before planning. Schema + fake integration proven; live wiring deferred so S5-013 convergence behavior stays untouched.
- `purpose_model_classes` map (S5-008) not consumed by any live cheap-model caller. Wiring deferred until cheap-model provider is configured.
- Multi-word aria-label regex fix applied in S5-010; further locator-prioritization work deferred.

## 11. Final recommendation

**Close Sprint 5.** 15/15 stories Done, 13/13 bugs Done, 365 cheap tests passing, real LLM contract probe green, paid E2E green with deterministic terminal `ask_user`. No code fix required during validation.
