# S6-0809 — Recovery Regression Guard and Architecture Drift Checks

## Story ID
S6-0809

## Objective
Prevent future recovery regressions and catch architecture drift.

## Regression tests

```
- no LLM-owned completion
- no frontend-inferred completion
- no record/code_update on unresolved failure
- bounded recovery loop (max 3 attempts)
- deterministic-first recovery always
- stale run/recovery rejection
- stale permission/instruction rejection
- S5 convergence still passes
- Cluster 7 permission/risk/capability gates still enforce
```

## What it contains

- Regression test suite (pytest)
- Architecture drift detection (imports, forbidden patterns)
- Convergence checks (S5 integration)
- Permission/risk enforcement checks
- Recovery loop depth limits
- Stale-safe validation checks

## What it must NOT contain

- New feature implementation
- Product code changes
- Paid E2E
- Broad refactoring

## Tests first

### Regression test suite

Unit regressions:

```
- permission_mode enforced (no bypass)
- risk_classifier deterministic
- unsupported capability cannot fake success
- recovery state blocks completion/recording
- deterministic recovery runs before LLM
- stale recovery rejected
```

Architecture drift:

```
- No recovery logic in agent.py
- No frontend decision-making in recovery
- No LLM-inferred completion state
- No code_update without backend evidence
- All recovery modules properly organized
```

Convergence:

```
- S5 controller tests still pass
- S5 prompt pack tests still pass
- Page intelligence integration still works
- Planning convergence still valid
```

Permission/Risk enforcement:

```
- strict mode asks before every change
- balanced mode asks for high-risk
- risk classifier gates execution
- capability registry enforced
```

### Acceptance

- Regression guard includes recovery suite
- All recovery tests are cheap/local (no paid LLM)
- Drift detection blocks commits with violations
- S5 convergence passing

## Acceptance criteria

- Regression test suite comprehensive (>50 tests)
- All regression tests passing
- Drift detection configured in CI
- S5 convergence validated
- Permission/risk enforcement verified
- 95% coverage on regression tests
- No paid E2E required for regression validation
- Sprint 6 regression guard passes

## Dependencies

- Requires: All of Cluster 8 (S6-0801 through S6-0808)
- Blocks: None (end of Cluster 8)

## Notes

- Regression guard is final gating point before Sprint 6 done
- Drift detection catches architectural violations early
- Design for CI: all tests run on every commit
- Scenario spec requires no unresolved failures, no fake success, no LLM-owned completion
