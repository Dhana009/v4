# S5-014 Prompt/cache-friendly stable prefix strategy

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 02_LLM_RUNTIME.md, prompt-caching best practices

## Evidence

Status: Done

Implemented:
- No runtime prompt-pack code change was required in this cluster; the existing `PromptPack` and prompt-pack builder seam already separated stable prefix from dynamic suffix.
- Added deterministic cache-strategy coverage proving the stable prefix stays reusable while dynamic context stays in the suffix.
- Verified the prefix hash is `sha256(stable_prefix)[:16]` and is unaffected by dynamic context changes.

Cache strategy:
- Stable prefix stays instruction-only.
- Dynamic context is rendered only through `render_dynamic_suffix(...)`.
- `prefix_hash` changes only when the stable prefix changes.

Prompt packs covered:
- `step_plan_normalizer.v1`
- `plan_diff_editor.v1`
- `recovery_diagnoser.v1`

Tests added/updated:
- `tests/test_prompt_cache_strategy.py`
- `tests/test_sprint5_llm_runtime_guardrails.py`

Commands run:
- `python -m py_compile tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py`
- `python -m pytest tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_correction_context.py tests/test_recovery_context.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_recovery_through_fake_model.py tests/test_fake_llm_factory.py -q`
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_recording_codegen_truth_contract.py -q`

Results:
- `py_compile`: passed
- `tests/test_prompt_cache_strategy.py tests/test_sprint5_llm_runtime_guardrails.py -q`: 34 passed
- prompt/context/policy/controller suite: 87 passed
- telemetry/backend safety suite: 90 passed

Interpretation:
- What this proves: stable prefixes are deterministic, cache-friendly, and insulated from dynamic runtime values.
- What remains: paid E2E still needs the controlled S5-013 acceptance flow.

Changed files:
- `tests/test_prompt_cache_strategy.py`
- `tests/test_sprint5_llm_runtime_guardrails.py`
- `.tasks-md/Done/S5-014 Prompt cache-friendly stable prefix strategy.md`

Commit:
- pending
