# S6-0006 Regression guard command set

**Sprint:** Sprint 6  
**Cluster:** 0 (Governance)  
**Type:** Documentation  
**Status:** Planning  
**Owner:** Testing Infrastructure  

---

## Purpose

Define the cheap regression suite that must pass after every Sprint 6 cluster. Prevents prior work from breaking.

---

## The command

Run this command after every cluster is complete:

```bash
# S6 Regression Guard Suite
REGRESSION_GUARD_SUITE=(
  "tests/test_backend_event_sequences.py"
  "tests/test_event_contract.py"
  "tests/test_recording_codegen_truth_contract.py"
  "tests/test_llm_runtime_controller_contract.py"
  "tests/test_prompt_pack_builder.py"
  "tests/test_prompt_pack_safety_rules.py"
  "tests/test_skill_escalation_contract.py"
  "tests/test_tool_schema_filter.py"
  "tests/test_planning_convergence_contract.py"
  "tests/test_page_intelligence_schema.py"
  "tests/test_page_intelligence_fake_integration.py"
  "tests/test_replay_one.py"
  "tests/test_deterministic_fast_path.py"
  "tests/test_dom_locator_contracts.py"
  "tests/test_frontend_plan_recovery_rendering.py"
  "tests/test_frontend_recorded_code_rendering.py"
)

python -m pytest "${REGRESSION_GUARD_SUITE[@]}" -q
```

Expected output:

```
365 passed in 2.5s
```

(Actual count may vary as new tests are added.)

---

## Covered layers

| Layer | Test file | Coverage |
|---|---|---|
| Backend event contract | `test_backend_event_sequences.py`, `test_event_contract.py` | Plan ready, clarification, recovery, recorded_step, code_update |
| Recording + codegen | `test_recording_codegen_truth_contract.py` | Step recording, code generation |
| LLM runtime | `test_llm_runtime_controller_contract.py` | Controller wiring, tool dispatch |
| Prompt packs | `test_prompt_pack_builder.py`, `test_prompt_pack_safety_rules.py` | Pack building, safety rules |
| Skill policy | `test_skill_escalation_contract.py` | Skill loading, escalation |
| Tool policy | `test_tool_schema_filter.py` | Tool filtering by purpose |
| Planning | `test_planning_convergence_contract.py` | Convergence narrowing, terminal output |
| Page Intelligence | `test_page_intelligence_schema.py`, `test_page_intelligence_fake_integration.py` | Schema building, fake integration |
| Replay | `test_replay_one.py` | Replay one step |
| Deterministic path | `test_deterministic_fast_path.py` | Fast path execution |
| Locator | `test_dom_locator_contracts.py` | Locator ranking, strategies |
| Frontend | `test_frontend_plan_recovery_rendering.py`, `test_frontend_recorded_code_rendering.py` | UI state rendering |

---

## When to run

After each cluster is done:

```bash
# Cluster 1 done, run regression guard
python -m pytest $REGRESSION_GUARD_SUITE -q

# All pass? Cluster 1 is safe.
# Any fail? Debug before moving to Cluster 2.
```

---

## Adding to CI

If CI is GitHub Actions, add to `.github/workflows/test.yml`:

```yaml
- name: Regression Guard
  run: python -m pytest tests/test_*.py tests/e2e/test_*.py -m "not paid_llm and not paid_e2e" -q
```

---

## What NOT to include

- ✗ Paid LLM tests (use RUN_PAID_LLM_CONTRACT=1)
- ✗ Paid browser E2E (use RUN_PAID_E2E_ACCEPTANCE=1)
- ✗ Network tests that depend on external services
- ✗ Flaky tests (wait list until stabilized)

---

## Expansion over time

As new clusters are completed, add tests to the guard:

```bash
# After Cluster 1 (runtime coverage):
REGRESSION_GUARD_SUITE+=(
  "tests/test_new_runtime_feature_contract.py"
)

# After Cluster 3 (Page Intelligence):
REGRESSION_GUARD_SUITE+=(
  "tests/test_page_intelligence_live_contract.py"
)

# After Cluster 4 (Journey planner):
REGRESSION_GUARD_SUITE+=(
  "tests/test_journey_planner_contract.py"
  "tests/e2e/test_multi_step_flow.py"  # cheap E2E only
)
```

---

## Out of scope

- No test implementation (other stories write tests)
- No product code changes
- No new test files yet

---

## Allowed files

- `.tasks-md/Testing/S6-REGRESSION-GUARD.md` (this output)

---

## Forbidden files

- No changes to test implementations
- No changes to product code

---

## Acceptance criteria

- [ ] Command is documented
- [ ] All focused test files are listed
- [ ] Suite runs locally in <3 minutes
- [ ] Expected output (pass count) is specified
- [ ] When to run is clear (after each cluster)
- [ ] How to add new tests is explained
- [ ] CI integration is documented
- [ ] File is stored in `.tasks-md/Testing/S6-REGRESSION-GUARD.md`

---

## Validation

After creation, test the command:

```bash
# Verify all test files exist
for f in tests/test_backend_event_sequences.py tests/test_event_contract.py; do
  [ -f "$f" ] && echo "✓ $f" || echo "✗ $f"
done

# Run the regression suite (should pass)
python -m pytest \
  tests/test_backend_event_sequences.py \
  tests/test_event_contract.py \
  tests/test_planning_convergence_contract.py \
  -q
```

---

## Stop conditions

- Test files missing or moved
- Suite takes >5 minutes to run
- Tests are flaky or environment-dependent
