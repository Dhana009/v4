# S6-0101 Purpose Registry Completeness Audit

**Sprint:** Sprint 6  
**Cluster:** 1  
**Story:** S6-0101  
**Date:** 2026-05-12  
**Status:** Complete  

---

## Audit Summary

All 14 required LLM purposes are **already registered** in `runtime/llm_runtime_controller.py`
via `_build_purpose_policy_map()` and the `PurposeRegistry` class. The `PurposeRegistry`
fails closed on unknown purposes (raises `ValueError`). All 14 purposes have complete
policy metadata including model_class, context_policy, skill_policy, tool_policy,
output_schema, backend_validator, fallback, retry_policy, and telemetry_fields.

**Overall status: 14/14 purposes DONE in policy map. Registry fail-closed: YES.**

---

## Purpose Audit Matrix

| Purpose ID | Current call site | Controller-owned? | Model class | Context level | Skills | Tools (planning phase) | Schema | Validator | Fallback | Tests found | Gaps |
|---|---|---|---|---|---|---|---|---|---|---|---|
| intent_classifier | agent.py via LLMRuntimeController | YES | cheap | compact | prompt_persona_skill_loading | () — no tools | intent_classifier.v1 | schema_validator | fail_closed | test_llm_runtime_controller_contract.py | No dedicated schema/validator file; policy declared inline |
| clarification_generator | agent.py via LLMRuntimeController | YES | cheap | compact | prompt_persona_skill_loading | PLAN_REVIEW_ONLY | clarification_generator.v1 | schema_validator | fail_closed | test_llm_runtime_controller_contract.py | No focused negative tests for "one question only" constraint |
| page_intelligence_summarizer | agent.py via LLMRuntimeController | YES | cheap | compact | locator_strategy | READ_ONLY_DOM | page_intelligence_summarizer.v1 | schema_validator | fail_closed | test_page_intelligence_fake_integration.py | No browser-mutation tool exclusion test |
| page_validation_recommender | agent.py via LLMRuntimeController | YES | main | compact | locator_strategy | browser_get_state, dom_extract, ask_user | page_validation_recommender.v1 | schema_validator | fail_closed | (none found for this specific purpose) | Missing dedicated tests |
| journey_planner | agent.py via LLMRuntimeController | YES | main | compact | prompt_persona_skill_loading | STEP_PLAN_TOOL_NAMES | journey_planner.v1 | schema_validator | fail_closed | test_planning_convergence_contract.py | No test: "no execution tools" constraint |
| step_plan_normalizer | agent.py via LLMRuntimeController | YES | main | compact | prompt_persona_skill_loading | STEP_PLAN_TOOL_NAMES | step_plan_normalizer.v1 | schema_validator | fail_closed | test_planning_convergence_contract.py, test_sprint5_llm_runtime_guardrails.py | Convergence tests exist; need stable step ID preservation test |
| plan_diff_editor | agent.py via LLMRuntimeController | YES | main | compact | prompt_persona_skill_loading | () — no browser tools | plan_diff_editor.v1 | schema_validator | fail_closed | (partial in controller contract) | No test: cannot silently drop/reorder child operations |
| locator_specialist | agent.py / runtime/agent_locator_handlers.py via LLMRuntimeController | YES | main | compact | locator_strategy | browser_get_state, dom_extract, locator_find, locator_validate, ask_user | locator_specialist.v1 | schema_validator | fail_closed | test_agent_locator_handler_contract.py, test_dom_locator_contracts.py | No test: gets no action tools |
| custom_assertion_planner | agent.py via LLMRuntimeController | YES | main | compact | prompt_persona_skill_loading + locator_strategy | browser_get_state, dom_extract, locator_find, locator_validate, ask_user | custom_assertion_planner.v1 | schema_validator | fail_closed | test_assertion_flow.py | No test: unsupported assertion → capability_gap |
| execution_driver | agent.py via LLMRuntimeController | YES | main | compact | prompt_persona_skill_loading | EXECUTION_DRIVER_PLANNING_TOOL_NAMES; executing phase: action_assert, action_click, action_fill | execution_driver.v1 | schema_validator | fail_closed | (partial in controller contract) | No test: blocked outside executing phase |
| recovery_diagnoser | runtime/recovery_manager.py via LLMRuntimeController | YES | main | compact | prompt_persona_skill_loading | RECOVERY_ONLY | recovery_diagnoser.v1 | schema_validator | fail_closed | test_recovery_manager_contract.py, test_recovery_through_fake_model.py | No test: cannot emit recorded/completed |
| replay_repair_specialist | recording/replay.py (partial) | PARTIAL | main | compact | prompt_persona_skill_loading | RECOVERY_ONLY | replay_repair_specialist.v1 | schema_validator | fail_closed | test_replay_one.py | Not fully controller-owned; no test: cannot mutate recording directly |
| user_response_writer | agent.py via LLMRuntimeController | YES | cheap | compact | prompt_persona_skill_loading | ask_user only | user_response_writer.v1 | schema_validator | fail_closed | (partial) | No test: cannot claim execution success |
| trace_summarizer | agent.py via LLMRuntimeController | YES | cheap | compact | prompt_persona_skill_loading | () — no tools | trace_summarizer.v1 | schema_validator | fail_closed | test_frontend_trace_display.py (partial) | No test: cannot mutate runtime truth |

---

## Key Findings

### 1. Registry and fail-closed: DONE
- `ALLOWED_PURPOSES` tuple defines all 14 purposes (lines 29-44)
- `PurposeRegistry.register()` raises `ValueError` for unknown purposes (line 360-361)
- `_resolve_policy()` raises `ValueError` for unregistered purposes (line 548-550)
- `LLMRuntimeController.call()` validates purpose against registry (line 1166-1167)

### 2. Policy completeness: DONE (all 14 have required fields)
- `_purpose_policy()` produces: purpose_id, model_class, context_policy, skill_policy, tool_policy, output_schema, backend_validator, fallback, retry_policy, telemetry_fields
- All purposes use `schema_validator` as validator_id
- All purposes use `fail_closed` as fallback
- All purposes have retry_policy with schema_retry_limit=1

### 3. Call-site status
- `llm.py`: direct OpenAI call — **NOT controller-owned** (legacy wrapper)
- `a.py`: direct OpenAI call — **NOT controller-owned** (scratch file, dead code)
- `llm/client.py`: direct OpenAI call — **NOT controller-owned** (legacy wrapper)
- `runtime/model_router.py`: direct provider call inside router — **controller-owned path**
- `agent.py`: uses `LLMRuntimeController` — **controller-owned**
- `runtime/recovery_manager.py`: uses controller — **controller-owned**
- `recording/replay.py`: partial, needs verification — **PARTIAL**

### 4. Missing dedicated module files
- `runtime/llm_purpose_policy.py` — does NOT exist yet (policy logic is in llm_runtime_controller.py)
- `runtime/llm_policy_registry.py` — does NOT exist yet (registry is in llm_runtime_controller.py)
- Cluster 1 stories S6-0102+ will create these as dedicated modules

### 5. Missing tests (gaps driving S6-0103..S6-0106)
- No test: `intent_classifier` has no tools
- No test: `clarification_generator` one-question constraint
- No test: `user_response_writer` cannot claim execution success
- No test: `trace_summarizer` cannot mutate runtime truth
- No test: `page_validation_recommender` gets no browser-changing tools
- No test: `journey_planner` gets no execution tools
- No test: `plan_diff_editor` cannot drop/reorder child ops silently
- No test: `locator_specialist` gets no action tools
- No test: `execution_driver` blocked outside executing phase
- No test: `recovery_diagnoser` cannot emit recorded/completed
- No test: `replay_repair_specialist` cannot mutate recording directly

---

## Classification Summary

| Status | Count | Purposes |
|---|---|---|
| DONE | 11 | intent_classifier, clarification_generator, page_intelligence_summarizer, page_validation_recommender, journey_planner, step_plan_normalizer, plan_diff_editor, custom_assertion_planner, execution_driver, user_response_writer, trace_summarizer |
| PARTIAL | 2 | locator_specialist (call site partial), replay_repair_specialist (controller ownership partial) |
| MISSING | 0 | — |
| UNKNOWN | 1 | recovery_diagnoser (needs further replay.py verification) |

**Registry readiness: 14/14 declared. Tests: 14/14 gaps identified. Implementation: S6-0102 creates dedicated modules.**

---

## Recommended Actions for S6-0102+

1. Create `runtime/llm_purpose_policy.py` with TypedDict `LLMPurposePolicy`
2. Create `runtime/llm_policy_registry.py` with `LLMPolicyRegistry` class and all 14 entries
3. Write tests for all policy constraints (S6-0103 through S6-0106)
4. Add guard tests for `replay_repair_specialist` controller ownership (S6-0107)
5. Classify `llm.py`, `a.py`, `llm/client.py` as legacy/dead code in call-site inventory

---

## Validation Evidence

```bash
# Registry syntax
python -m py_compile runtime/llm_runtime_controller.py  # OK
python -m py_compile runtime/tool_schema_policy.py      # OK
python -m py_compile runtime/skill_policy.py            # OK
python -m py_compile runtime/prompt_pack_builder.py     # OK
python -m py_compile runtime/model_router.py            # OK

# Controller tests
pytest tests/test_llm_runtime_controller_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py -q
# Result: 29 passed

# All 14 ALLOWED_PURPOSES confirmed in llm_runtime_controller.py lines 29-44
# PurposeRegistry fail-closed confirmed in lines 360-361, 548-550
```
