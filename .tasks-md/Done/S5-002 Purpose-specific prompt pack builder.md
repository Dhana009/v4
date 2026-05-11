# S5-002 Purpose-specific prompt pack builder

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, AGENTS.md token baseline, runtime/llm_runtime_controller.py

## Problem / Goal

**Problem:** All LLM calls receive the same heavy system prompt (~3496 tokens). This dominates per-call overhead.

**Goal:** Create compact prompt packs per purpose (stable prefix + minimal dynamic suffix). step_plan_normalizer pack should be ≤3000 tokens vs current ~3500.

## Scope

- Build prompt-pack builder module: `runtime/prompt_pack_builder.py`
- Implement step_plan_normalizer pack first (planning-specific rules only)
- Separate stable prefix (deterministic rules) from dynamic suffix (phase/context instructions)
- Preserve all safety rules and critical context
- Plan_diff_editor second if safe (pure plan-edit rules)

Out of scope:
- All 14 purpose packs at once — implement 2–3 as proof
- Removing safety rules or context required for correctness
- Changing output schema
- LLM behavior adaptation (packs are static templates)

## Evidence

Status: Done

Implemented:
- Added focused prompt-pack primitives in `runtime/prompt_packs.py`
- Added `runtime/prompt_pack_builder.py` with the first step-specific pack and dynamic context helper
- Wired `LLMRuntimeController` to apply the step-plan-normalizer pack after skill selection and before model call
- Added a narrow `agent.py` telemetry sync so the final `[LLM_TELEMETRY]` line reflects prompt-pack metadata and adjusted system prompt tokens

Prompt pack decision:
- Use a stable prefix + separate dynamic suffix template
- Keep the stable prefix deterministic and hash it with `sha256`
- Apply the pack only for `step_plan_normalizer` in this cluster
- Leave other purposes on their existing path

step_plan_normalizer pack:
- prompt_pack_id: `step_plan_normalizer.v1`
- version: `1`
- stable prefix: `PROMPT_PACK_ID`, `PROMPT_PACK_VERSION`, `NON_NEGOTIABLE_RUNTIME_RULES`, `ROLE`, `OUTPUT_EXPECTATION`, and `PLANNING_RULES`
- dynamic suffix: `DYNAMIC_PLANNING_CONTEXT` with user intent, selected context, page summary, queued steps, validated locators, skills loaded, skill levels, and output schema reminder
- prefix_hash: deterministic 16-char sha256 prefix hash of the stable prefix

Safety rules:
- Preserved the five non-negotiable runtime rules verbatim in the stable prefix
- Kept backend validation authority explicit
- Kept confirmation and no-execution semantics intact
- Did not add forbidden finality language

Telemetry:
- `prompt_pack_id`, `prompt_pack_version`, `prefix_hash`, `system_prompt_tokens`, `estimated_message_tokens`, and `estimated_input_tokens` now flow through the step-plan-normalizer controller result
- `agent.py` copies those fields back onto `ModelCallTelemetry` before the final log line is emitted
- Token report parsing remains unchanged and still accepts the enriched `[LLM_TELEMETRY]` line

Tests added/updated:
- `tests/test_prompt_pack_builder.py`
- `tests/test_prompt_pack_safety_rules.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_planning_through_controller_fake_model.py`

Commands run:
- `python -m py_compile runtime/prompt_pack_builder.py runtime/prompt_packs.py runtime/llm_runtime_controller.py agent.py tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py -q`
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_fake_llm_factory.py -q`
- `python -m pytest tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py -q`
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_recording_codegen_truth_contract.py -q`

Results:
- `py_compile`: passed
- `tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py -q`: 12 passed
- `tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_fake_llm_factory.py -q`: 48 passed
- `tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py -q`: 15 passed
- `tests/test_telemetry_breakdown.py tests/test_token_report.py -q`: 46 passed
- `tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_recording_codegen_truth_contract.py -q`: 44 passed

Interpretation:
- What token bucket this should reduce: system prompt bucket
- What remains for S5-005/S5-006/S5-014/S5-013: extend the pack strategy to additional purposes and then compare output quality in controlled follow-up work

Changed files:
- `runtime/prompt_packs.py`
- `runtime/prompt_pack_builder.py`
- `runtime/llm_runtime_controller.py`
- `agent.py`
- `tests/test_prompt_pack_builder.py`
- `tests/test_prompt_pack_safety_rules.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_planning_through_controller_fake_model.py`
- `.tasks-md/Done/S5-002 Purpose-specific prompt pack builder.md`

Commit:
- pending
