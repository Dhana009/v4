# S5-015 Sprint 5 regression guardrails

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 00_MASTER_INDEX.md non-negotiables, AGENTS.md token baseline

## Evidence

Status: Done

Implemented:
- Added a focused deterministic regression suite in `tests/test_sprint5_llm_runtime_guardrails.py`.
- The suite validates prompt safety, tool exposure safety, skill policy safety, context boundary safety, telemetry safety, and controller boundary safety using only local fakes and existing runtime helpers.
- No runtime behavior changes were required for the guardrails; the current runtime already exposes the seams needed to prove the Sprint 5 invariants.

Guardrails:
- Prompt safety: all registered prompt packs keep the five non-negotiable runtime rules and avoid forbidden finality language.
- Tool exposure safety: compact correction/recovery/page-intelligence policies stay narrow and purpose-specific.
- Skill policy safety: compact-only purposes do not escalate by default, unknown purposes stay minimal, and full-skill loading requires an explicit allowed reason.
- Context boundary safety: correction and recovery payloads stay compact and do not leak full DOM or unrelated history.
- Telemetry safety: controller and token-report metadata preserve prompt pack identity, skill levels, and cache fields.
- Controller boundary safety: raw-response preservation still works, tool calls survive, and malformed responses cannot be misread as success.

Paid E2E readiness checklist:
- Fake planning/correction/recovery tests pass.
- Prompt pack safety tests pass.
- Cache strategy tests pass.
- Tool policy guardrails pass.
- Skill policy guardrails pass.
- Context boundary guardrails pass.
- Telemetry/token report guardrails pass.
- No paid E2E has been run yet.
- Next story can be S5-013 controlled paid E2E.

Tests added/updated:
- `tests/test_sprint5_llm_runtime_guardrails.py`
- `tests/test_prompt_cache_strategy.py`

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
- What this protects: prompt, tool, skill, context, telemetry, and controller regressions are now caught before any paid E2E work.
- What remains: controlled paid E2E is still the next open step, and it should only start after S5-013 is explicitly approved.

Changed files:
- `tests/test_sprint5_llm_runtime_guardrails.py`
- `tests/test_prompt_cache_strategy.py`
- `.tasks-md/Board/SPRINT-005-PLAN.md`
- `.tasks-md/Done/S5-015 Sprint 5 regression guardrails.md`

Commit:
- pending
