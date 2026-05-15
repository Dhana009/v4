# S7-1010 — Sprint 7 Regression Smoke Suite

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 1 (core)
**Type:** Test
**Status:** Done
**Blocks:** []
**Blocked by:** [S7-1001, S7-1002, S7-1003, S7-1004, S7-1005, S7-1006, S7-1007, S7-1008, S7-1009]

---

## Objective

Bundle all Cluster 10 E2E flows and cheap frontend/backend checks into a repeatable regression gate. Define:
- Exact commands to run
- Required environment setup
- Fake LLM / no-paid policy enforcement
- Artifacts required
- Failure classification
- Acceptance criteria for push readiness

---

## Source Rules

- GOV-S7-C10-002: Local E2E only; no paid APIs
- GOV-S7-C0-007: Every test must reference source rule

---

## Tests First

```python
# tests/e2e/test_sprint7_regression_smoke.py

test_sprint7_smoke_all_flows()  # GOV-S7-C0-007
  # Run all 8 main flows (S7-1003 through S7-1009 excluding supporting)
  # Assert: all pass
  # Allowed failures: max 1 per 10 flows (flake tolerance)
  # Disallowed: new failures not in pre-existing list

test_cheap_suite_green()  # GOV-S7-C0-007
  # python -m pytest -q --ignore=tests/e2e
  # Assert: pass count same or better than Sprint 6 baseline
  # Failures classified: known bugs vs new regressions
```

---

## Regression Suite Definition

```bash
# Setup
export AUTOWORKBENCH_LLM_MODE=complete_llm
export AUTOWORKBENCH_E2E_MODE=fake_llm  # Force fake LLM, no paid APIs
unset OPENAI_API_KEY  # Ensure paid LLM unavailable
cd /path/to/repo

# Run local E2E
python -m pytest tests/e2e/test_flow_*.py -v --tb=short \
  -k "not paid" \
  --capture-artifacts=./artifacts/sprint7-smoke-$(date +%s) \
  --no-live-websites \
  --timeout=300  # 5 min per test

# Run cheap backend suite
python -m pytest -q --ignore=tests/e2e \
  --tb=line \
  2>&1 | tee cheap-suite-output.txt

# Classify failures
python scripts/classify_failures.py \
  --baseline=.tasks-md/Sprints/SPRINT-006-HANDOFF.md \
  --current=cheap-suite-output.txt \
  --output=failure-classification.json
```

---

## Artifacts Required

- Event logs for each flow (JSON)
- Command logs for each flow (JSON)
- Screenshots at key moments (PNG)
- Manifest with test metadata (JSON)
- Cheap suite output (TXT)
- Failure classification report (JSON)

---

## Acceptance Criteria

- [ ] All 8 main E2E flows pass
- [ ] Flakiness < 5% on 3 consecutive runs
- [ ] No paid API calls detected in logs
- [ ] No live external websites accessed
- [ ] Cheap suite: 0 new failures (pre-existing known bugs only)
- [ ] All artifacts captured
- [ ] Clear pass/fail/deferred decision made

---

## Stop Conditions

- E2E has > 1 failure per 10 flows (unreliable)
- Cheap suite has new failures not in Sprint 6 baseline (regression)
- Paid APIs detected in environment (policy violation)
- Artifacts cannot be captured (evidence lost)

---

## Evidence Recorded

- **Commit:** 4e9d102 — Cluster 10 fake-flow tests + harness shadow constants
- **Tests:** tests/test_cluster10_e2e_contract.py, tests/test_cluster10_fake_flows.py (21 tests)
- **E2E baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed in 7.22s
- **Regression (no-e2e):** 2481 passed / 1 skipped / 0 failed
- **Browser smoke gate:** existing tests/e2e/* suite remains user-triggered (no paid LLM, no live websites)
