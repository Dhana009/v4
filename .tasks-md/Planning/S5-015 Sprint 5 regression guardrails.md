# S5-015 Sprint 5 regression guardrails

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 00_MASTER_INDEX.md non-negotiables, AGENTS.md token baseline

## Problem / Goal

**Problem:** Sprint 5 introduces major prompt/context/skill changes. Need guardrails to catch regressions before they ship: token bloat, missing safety rules, unsafe tool exposure, wrong context policy.

**Goal:** Create CI-friendly regression tests that catch: token budgets exceeded, safety rules missing, forbidden tools exposed by purpose, context policy violations.

## Scope

- Token budget gate: prompt pack ≤budget for purpose (e.g., step_plan_normalizer ≤3000)
- Safety rule gate: all critical rules present in prompt
- Tool policy gate: forbidden tools not exposed (correction can't see execute tools)
- Context policy gate: wrong context level not applied (recovery gets full history)
- Skill policy gate: COMPACT_ONLY_PURPOSES don't load full skills
- Phase instruction gate: phase instructions present for all phases

Out of scope:
- Hardcoded token thresholds (allow parameterization)
- Changing acceptance criteria mid-sprint

## Required unit tests

- `test_token_budget_regression.py`:
  - Each purpose pack ≤defined budget
  - Prompt tokens estimated correctly
- `test_safety_rule_regression.py`:
  - All critical safety rules present in all packs
  - Rules: "LLM doesn't decide completion", "backend owns truth", "no unconfirmed action"
- `test_tool_policy_regression.py`:
  - plan_diff_editor doesn't expose execute tools
  - recovery_diagnoser doesn't expose planning tools
- `test_context_policy_regression.py`:
  - recovery context doesn't include full planning history
  - correction context includes active plan only
- `test_skill_policy_regression.py`:
  - COMPACT_ONLY_PURPOSES don't load full skills (escalation required)
- `test_phase_instruction_regression.py`:
  - All phases have defined instructions

## Required contract tests

- `test_purpose_registry_contract.py`:
  - All 14 purposes have defined policy
  - No missing fields in policy (model_class, token_budget, context_policy, tool_policy)

## Required integration tests

- `test_regression_gates_integration.py`:
  - All regression tests can run together
  - No false positives

## Fixture/page needs

None.

## Paid E2E requirement

None.

## Acceptance criteria

- [ ] Token budget gates created and passing
- [ ] Safety rule gates created and passing
- [ ] Tool policy gates created and passing
- [ ] Context policy gates created and passing
- [ ] Skill policy gates created and passing
- [ ] Phase instruction gates created and passing
- [ ] All gates run in CI without real LLM
- [ ] No false positives/negatives

## Evidence

Will include:
- Regression test suite in `tests/regression_gates/`
- Gate pass/fail report
- CI configuration to run gates on every commit
- Documentation of each gate

## Verification commands/results

```bash
pytest tests/regression_gates/ -v
# All gates should pass

# Run in CI:
# Add to .github/workflows/test.yml (or equivalent):
# pytest tests/regression_gates/ -v --tb=short

# Expected output:
# test_token_budget_regression.py::test_step_plan_normalizer_budget PASSED
# test_safety_rule_regression.py::test_safety_rules_present PASSED
# test_tool_policy_regression.py::test_correction_no_execute_tools PASSED
# ... (all gates pass)
```

## Risk

- **Low:** Gate thresholds may be too strict or too loose (adjust based on development)
- **Low:** False positives if gates are too broad (mitigated by focused tests)

## Mitigation

- Gates are parameterized (easy to adjust)
- Tests are explicit about what they check
- CI runs gates on every commit (early feedback)
