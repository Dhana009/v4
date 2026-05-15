# BUG-RUNTIME-002 Missing llm_policy_gateway seam in __new__ AgentLoop tests

Status: Done
Sprint: Sprint 3
Type: Bug
Severity: P1
Owner: Runtime / Test Infra
Priority: P1
Started: 2026-05-08 21:15 IST

## Source / Contract violated

- Sprint 3 live gateway seam must not break existing backend/runtime contract tests.
- Tests are enforcement layer; adding a runtime seam must not require broad fixture rewrites.

## Expected

`AgentLoop.run()` should continue to work in focused unit tests that construct loops via `AgentLoop.__new__` and stub only the fields they need.

## Actual

Broad non-E2E verification failed with `AttributeError: 'AgentLoop' object has no attribute 'llm_policy_gateway'` across:

- `tests/test_code_update.py`
- `tests/test_multi_action_safety.py`
- `tests/test_plan_correction.py`

## Root cause

The new live policy gateway seam was added in `__init__`, but many long-standing focused tests build `AgentLoop` via `__new__` and never call `__init__`.

## Fix plan

- Add a lazy default gateway fallback in `run()` for `__new__`-based loops.
- Re-run the failing focused runtime suites.

## Verification

- Focused tests:
  - `python -m pytest tests/test_code_update.py tests/test_multi_action_safety.py tests/test_plan_correction.py tests/test_recorded_step_model.py -q`
- Broad non-E2E:
  - `python -m pytest tests/ --ignore=tests/e2e -q`
- Result:
  - `run()` now lazily initializes a default gateway for `__new__`-based loops
  - the affected runtime suites passed again
