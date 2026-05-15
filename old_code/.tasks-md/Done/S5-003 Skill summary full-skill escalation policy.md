# S5-003 Skill summary/full-skill escalation policy

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, runtime/skill_policy.py, runtime/skill_selector.py

## Evidence

Status: Done

Implemented:
- Added `runtime/skill_summaries.py` with compact controller-owned summaries for the existing runtime skill names.
- Added `runtime/skill_selector.py` with a pure `select_skills_for_purpose(...)` selector and `build_skill_prompt(...)`.
- Extended `runtime/skill_policy.py` with:
  - `MINIMAL_CORE_SKILLS`
  - `FULL_SKILL_ESCALATION_PURPOSES`
  - `FULL_SKILL_ESCALATION_REASONS`
  - `get_default_skill_names(...)`
  - `get_skill_levels_for_names(...)`
  - `can_escalate_to_full_skills(...)`
- Updated `runtime/llm_runtime_controller.py` so controller-owned calls:
  - replace the incoming full system prompt with compact purpose-specific skill text by default
  - preserve the original full prompt only on explicit retry/escalation for allowed purposes
  - keep compact-only purposes such as `plan_diff_editor` from escalating to the full prompt
  - emit `skills_loaded` and `skill_levels` in controller telemetry

Skill policy decision:
- Compact summaries are now the default controller prompt surface.
- Unknown purposes fall back to minimal compact core skill guidance.
- Recovery/debug purposes get compact debug guidance added by selector policy without widening registry contracts.
- Full prompt preservation requires an explicit escalation reason such as `schema_retry` and a purpose that permits escalation.
- `plan_diff_editor` remains compact-only even on retry.

Telemetry:
- Controller telemetry now emits:
  - `skills_loaded`
  - `skill_levels`
- Existing `skill_tokens` accounting in `runtime.telemetry.py` was left backward compatible and unchanged.

Tests added/updated:
- `tests/test_skill_selector.py`
  - purpose-to-skill-level mapping
  - compact-only protection
  - recovery/debug skill addition
  - unknown-purpose fallback
- `tests/test_skill_escalation_contract.py`
  - compact prompt replacement for `step_plan_normalizer`
  - retry-time full prompt preservation on explicit escalation
- Existing regression coverage also passed:
  - `tests/test_skill_loading_policy.py`
  - `tests/test_llm_runtime_controller_contract.py`
  - `tests/test_planning_through_controller_fake_model.py`

Commands run:
- `python -m py_compile runtime/skill_policy.py runtime/skill_summaries.py runtime/skill_selector.py runtime/tool_schema_policy.py runtime/llm_runtime_controller.py runtime/tool_registry.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py`
- `python -m pytest tests/test_skill_selector.py tests/test_skill_escalation_contract.py -q`
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_fake_llm_factory.py -q`
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_recording_codegen_truth_contract.py -q`
- `python -m pytest tests/test_skill_loading_policy.py tests/test_tool_registry.py tests/test_llm_planning_contracts.py -q`

Results:
- `tests/test_skill_selector.py tests/test_skill_escalation_contract.py -q`: 8 passed
- `tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_fake_llm_factory.py -q`: 46 passed
- `tests/test_telemetry_breakdown.py tests/test_token_report.py -q`: 46 passed
- `tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_recording_codegen_truth_contract.py -q`: 44 passed
- `tests/test_skill_loading_policy.py tests/test_tool_registry.py tests/test_llm_planning_contracts.py -q`: 40 passed

Interpretation:
- What token bucket this should reduce:
  - skill bucket
- What remains for S5-002:
  - prompt packs still do not exist
  - stable prefix packing and explicit prompt pack IDs remain future work

Changed files:
- `runtime/skill_policy.py`
- `runtime/skill_summaries.py`
- `runtime/skill_selector.py`
- `runtime/llm_runtime_controller.py`
- `tests/test_skill_selector.py`
- `tests/test_skill_escalation_contract.py`
- `.tasks-md/Done/S5-003 Skill summary full-skill escalation policy.md`

Commit:
- pending
