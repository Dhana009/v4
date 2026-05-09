# S5-005 Context reuse and delta context for correction

Status: Planning
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

- [ ] Delta context builder module created
- [ ] Plan correction uses: active plan + correction text + edit rules only
- [ ] No full DOM unless target change mentioned
- [ ] Context tokens reduced for correction calls
- [ ] Silent drop guard and reorder guard preserved in rules
- [ ] Telemetry includes context_mode="correction_only"
- [ ] Output schema and safety rules unchanged

## Evidence

Will include:
- Delta context builder module
- Unit test output showing minimal context
- Contract test output showing edit rules
- Integration test telemetry with context_level
- Token estimate comparison: baseline correction context vs delta context

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
