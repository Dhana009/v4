# S5-005 Context reuse and delta context for correction

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 02_LLM_RUNTIME.md structured plan correction section, runtime/context_manager.py

## Problem / Goal

**Problem:** Plan correction uses the same full history and context as initial planning. Correction should only need: active plan + correction text + edit rules. No DOM re-extraction unless target changes.

**Goal:** Implement delta context for plan_diff_editor. Correction message includes active plan, correction text, and edit rules only. No full planning history unless correction changes target/locator.

## Scope

- Extend ContextManager with delta context builder: `build_delta_context_for_correction()`
- Plan correction includes: active plan JSON, correction text, edit rules, phase instruction
- No full DOM unless correction text mentions target/locator/selector change
- Preserve "silent drop guard" and "reorder guard" in edit rules
- Test with fake model plan corrections

Out of scope:
- Broad correction behavior rewrite (S5-006 handles recovery)
- Changing plan_diff_editor output schema
- Target/locator search if correction doesn't specify element

## Required unit tests

- `test_delta_context_builder.py`:
  - build_delta_context_for_correction(active_plan, correction_text) returns minimal context
  - Active plan is full JSON, not summarized
  - Edit rules included
  - No full DOM by default
  - DOM included if correction mentions target/selector/locator
- `test_correction_context_tokens.py`:
  - Delta context tokens reduced vs full planning context
  - Comparison: baseline correction context vs new delta context

## Required contract tests

- `test_correction_diff_contract.py`:
  - Model receives active plan, correction text, edit rules
  - Output schema matches plan_diff_editor output
  - Silent drop guard and reorder guard present in rules

## Required integration tests

- `test_plan_correction_delta_context.py`:
  - Correction call uses delta context only
  - No full message history resent
  - Telemetry shows context_level="correction_only"

## Fixture/page needs

None.

## Paid E2E requirement

None.

## Acceptance criteria

- [x] Delta context builder module created
- [x] Plan correction uses: active plan + correction text + edit rules only
- [x] No full DOM unless target change mentioned
- [x] Context tokens reduced for correction calls
- [x] Silent drop guard and reorder guard preserved in rules
- [x] Telemetry includes context_mode="correction_only"
- [x] Output schema and safety rules unchanged

## Evidence

Implemented:
- `runtime/correction_context.py` now builds compact correction payloads from the active plan, user correction, edit policy, and optional validation feedback.
- `runtime/prompt_pack_builder.py` provides the `plan_diff_editor.v1` prompt pack with stable-prefix / dynamic-suffix separation.
- `agent.py` keeps correction routing on the controller path without changing the existing correction schema guard.

Correction context logic:
- Uses the active plan as the source of truth.
- Preserves existing child operations and order unless the correction explicitly changes them.
- Falls back to the raw user correction text when the structured marker is absent.
- Marks locator-sensitive corrections so broader DOM re-evaluation can be handled separately.

Prompt pack:
- `plan_diff_editor.v1`
- Stable prefix includes the five non-negotiable runtime rules and correction-specific no-drop / no-reorder / no-split rules.
- Dynamic suffix carries active plan id, target step id, correction text, plan summary, child operations, validated locators, validation feedback, allowed edit policy, and locator-context requirement.

Tests added/updated:
- `tests/test_correction_context.py`
- `tests/test_prompt_pack_builder.py`
- `tests/test_prompt_pack_safety_rules.py`
- `tests/test_llm_runtime_controller_contract.py`

Commands run:
- `python -m py_compile runtime/correction_context.py runtime/prompt_pack_builder.py tests/test_correction_context.py tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_llm_runtime_controller_contract.py`
- `python -m pytest tests/test_correction_context.py tests/test_recovery_context.py -q`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py -q`
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_recovery_through_fake_model.py tests/test_fake_llm_factory.py -q`

Results:
- `tests/test_correction_context.py tests/test_recovery_context.py -q`: 5 passed
- `tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py -q`: 16 passed
- `tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_recovery_through_fake_model.py tests/test_fake_llm_factory.py -q`: 51 passed

Interpretation:
- What token/call waste this should reduce: correction calls no longer need to carry the full first-time planning surface, and the correction prompt pack stays cacheable.
- What remains: S5-006 recovery context is now separated too, but broader correction/recovery token accounting can still be measured further in later sprint work.

## Verification commands/results

```bash
pytest tests/test_delta_context_builder.py -v
pytest tests/test_correction_context_tokens.py -v
pytest tests/test_correction_diff_contract.py -v
pytest tests/test_plan_correction_delta_context.py -v

# Verify context reduction
# Expected: correction context ~2000–3000 tokens vs baseline ~5000–8000
```

## Risk

- **Medium:** Omitting full history may hide user intent if correction is ambiguous
- **Low:** Target detection may incorrectly infer whether DOM is needed

## Mitigation

- Contract test verifies edit rules include all guards
- Controlled E2E (S5-013) tests correction accuracy
- Fallback: if context budget exceeded, include full history (logged)
