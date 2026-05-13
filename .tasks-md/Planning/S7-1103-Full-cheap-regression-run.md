# S7-1103 — Full Cheap Regression Run

**Sprint:** Sprint 7
**Cluster:** 11
**Tier:** 1 (core)
**Type:** Test
**Status:** Planning
**Blocks:** [S7-1106, S7-1107]
**Blocked by:** [All Clusters 1–10]

---

## Objective

Run full cheap test suite (all unit, contract, integration tests; skip E2E). Classify all failures: pre-existing vs new regressions. Expected: 0 new failures vs Sprint 6 baseline.

---

## Source Rules

- GOV-S7-C0-007: Every test failure must be classified and tracked

---

## Tests First

```bash
# Run full suite
python -m pytest -q --ignore=tests/e2e 2>&1 | tee cheap-suite-final.txt

# Classify
python scripts/classify_failures.py \
  --baseline=SPRINT-006-HANDOFF.md \
  --current=cheap-suite-final.txt \
  --output=failure-classification.json
```

---

## Acceptance Criteria

- [ ] All tests run without timeout
- [ ] 0 new failures
- [ ] All pre-existing failures classified
- [ ] BUG tickets created for any new failures

---

## Evidence Required

- [ ] cheap-suite-final.txt (test output)
- [ ] failure-classification.json
- [ ] Report committed to .tasks-md/Artifacts/C11/

---

## Stop Conditions

- > 5 new test failures (regression; must fix before push)
- Timeout or infrastructure error (must debug)
