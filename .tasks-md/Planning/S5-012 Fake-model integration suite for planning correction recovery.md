# S5-012 Fake-model integration suite for planning/correction/recovery

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 02_LLM_RUNTIME.md, runtime/llm_runtime_controller.py

## Problem / Goal

**Problem:** Real LLM calls cost money. Development currently relies on occasional paid E2E. Sprint 5 changes (prompt packs, skill escalation, context deltas) need comprehensive testing without paid LLM.

**Goal:** Build fake-model suite that simulates planning, correction, and recovery outputs. LLMRuntimeController routes through fake model. Tests verify: flow works end-to-end, schema is valid, backend validation applies, Step Runner makes truth decisions.

## Scope

- Extend FakeLLM in tests to handle: planning, correction, recovery purposes
- Fake planning: returns valid plan_ready schema
- Fake correction: returns corrected_plan schema
- Fake recovery: returns recovery_proposal schema
- Integration tests: flow end-to-end using fake model
- Negative tests: malformed fake output is rejected
- Step Runner validation tests: fake output still goes through validation

Out of scope:
- Replicating real LLM reasoning (fake is deterministic)
- True quality/correctness (S5-013 does controlled E2E for that)

## Required unit tests

- `test_fake_llm_planning_output.py`:
  - FakeLLM(purpose="step_plan_normalizer") returns plan_ready schema
  - Output is valid JSON
  - Includes all required fields
- `test_fake_llm_correction_output.py`:
  - FakeLLM(purpose="plan_diff_editor") returns corrected_plan schema
  - Output matches plan_diff_editor contract
- `test_fake_llm_recovery_output.py`:
  - FakeLLM(purpose="recovery_diagnoser") returns recovery_proposal schema
  - Output matches recovery contract

## Required contract tests

- `test_fake_model_schema_validation.py`:
  - Fake planning output matches step_plan_normalizer.v1 schema
  - Fake correction output matches plan_diff_editor.v1 schema
  - Fake recovery output matches recovery_diagnoser.v1 schema
- `test_fake_model_malformed_rejection.py`:
  - Missing required fields → schema validation failure
  - Invalid step structure → rejected
  - Invalid target → rejected

## Required integration tests

- `test_planning_through_fake_model.py`:
  - User intent → fake planning → plan_ready → confirmation flow
  - All messages valid
  - No real LLM involved
- `test_correction_through_fake_model.py`:
  - Active plan + correction → fake model → corrected_plan → confirmation
  - Correction rules applied
  - No real LLM involved
- `test_recovery_through_fake_model.py`:
  - Failed step + error → fake recovery → proposal → Step Runner validation
  - Recovery proposal is actionable
  - Step Runner makes final decision
- `test_fake_model_full_flow_e2e.py`:
  - End-to-end: planning → correction → recovery using fake model
  - All phases work
  - No paid LLM

## Fixture/page needs

Fixture pages from S5-011.

## Paid E2E requirement

None.

## Acceptance criteria

- [ ] FakeLLM module supports planning/correction/recovery purposes
- [ ] All fake outputs match required schemas
- [ ] Malformed outputs are rejected by schema validation
- [ ] Integration tests cover planning/correction/recovery end-to-end
- [ ] All tests pass without real LLM
- [ ] Fake model is deterministic and reproducible
- [ ] Step Runner validation still applies to fake output

## Evidence

Will include:
- FakeLLM implementation
- Unit test output showing schema validity
- Contract test output showing schema validation
- Integration test output showing end-to-end flows
- Telemetry showing fake model calls

## Verification commands/results

```bash
pytest tests/test_fake_llm_planning_output.py -v
pytest tests/test_fake_llm_correction_output.py -v
pytest tests/test_fake_llm_recovery_output.py -v
pytest tests/test_fake_model_schema_validation.py -v
pytest tests/test_fake_model_malformed_rejection.py -v
pytest tests/test_planning_through_fake_model.py -v
pytest tests/test_correction_through_fake_model.py -v
pytest tests/test_recovery_through_fake_model.py -v
pytest tests/test_fake_model_full_flow_e2e.py -v

# All should pass without calling real LLM
```

## Risk

- **Low:** Fake model may not catch real-LLM edge cases
- **Low:** Test coverage may not match real usage patterns

## Mitigation

- Contract tests are strict about schema
- Controlled E2E (S5-013) validates real-LLM behavior
- Fake-model suite is supplement, not replacement for E2E
