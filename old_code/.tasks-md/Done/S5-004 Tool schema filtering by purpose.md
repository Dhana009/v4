# S5-004 Tool schema filtering by purpose

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, runtime/llm_runtime_controller.py, runtime/tool_schema_policy.py, runtime/tool_registry.py

## Evidence

Status: Done

Implemented:
- Added `runtime/tool_schema_policy.py` as the focused purpose-to-tool policy table.
- Updated `runtime/llm_runtime_controller.py` purpose policies to use the focused tool policy table rather than broad local defaults.
- Enforced these key planning slices:
  - `plan_diff_editor` → zero tools
  - `step_plan_normalizer` → planning-safe tools only
  - `recovery_diagnoser` / `replay_repair_specialist` → `browser_get_state`, `ask_user`
  - `page_intelligence_summarizer` → `dom_extract` only
- Kept existing phase filtering in `runtime/tool_registry.py` intact; purpose reduction still composes through `allowed_tool_names`.

Tool policy decision:
- Chose a focused runtime helper module instead of adding more conditional logic to `agent.py`.
- Purpose policy stays declarative in one table.
- Unknown purpose falls back safely to no extra planning tools in the helper.
- Existing phase guardrails remain active and were not widened.

Tests added/updated:
- `tests/test_tool_schema_filter.py`
  - zero-tool `plan_diff_editor`
  - recovery-only tool slice
  - DOM-only page intelligence
  - planning-safe `step_plan_normalizer`
  - token estimate reduction vs full schema
- `tests/test_tool_policy_contract.py`
  - registry contract matches helper table
  - unknown purpose fails safe
- Existing regression coverage also passed:
  - `tests/test_tool_registry.py`
  - `tests/test_llm_runtime_controller_contract.py`
  - `tests/test_llm_planning_contracts.py`

Commands run:
- `python -m py_compile runtime/skill_policy.py runtime/skill_summaries.py runtime/skill_selector.py runtime/tool_schema_policy.py runtime/llm_runtime_controller.py runtime/tool_registry.py tests/test_skill_selector.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py`
- `python -m pytest tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py -q`
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_fake_llm_factory.py -q`
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_recording_codegen_truth_contract.py -q`
- `python -m pytest tests/test_skill_loading_policy.py tests/test_tool_registry.py tests/test_llm_planning_contracts.py -q`

Results:
- `tests/test_tool_schema_filter.py tests/test_tool_policy_contract.py -q`: 7 passed
- `tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_fake_llm_factory.py -q`: 46 passed
- `tests/test_telemetry_breakdown.py tests/test_token_report.py -q`: 46 passed
- `tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_recording_codegen_truth_contract.py -q`: 44 passed
- `tests/test_skill_loading_policy.py tests/test_tool_registry.py tests/test_llm_planning_contracts.py -q`: 40 passed

Interpretation:
- What token bucket this should reduce:
  - tool schema bucket
- What remains for S5-002:
  - purpose-specific prompt packs still do not exist
  - tool policy now exists, so prompt-pack work can encode these narrower tool slices directly

Changed files:
- `runtime/tool_schema_policy.py`
- `runtime/llm_runtime_controller.py`
- `tests/test_tool_schema_filter.py`
- `tests/test_tool_policy_contract.py`
- `.tasks-md/Done/S5-004 Tool schema filtering by purpose.md`

Commit:
- pending
