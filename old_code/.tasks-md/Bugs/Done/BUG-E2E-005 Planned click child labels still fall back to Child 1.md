# BUG-E2E-005 Planned click child labels still fall back to Child 1

Status: Done
Sprint: Sprint 3
Type: Bug
Severity: P1
Owner: Plan Builder / E2E
Priority: P1
Started: 2026-05-08 21:23 IST

## Expected

Planned click children shown in the plan review card should use a human label like `Get started`, not a technical locator string that the panel later discards.

## Actual

`correction_assert_then_click_flow` initial plan review child description rendered as `Child 1`.

Artifact:

`test-results/autoworkbench-e2e/correction_assert_then_click_flow-20260508-203501-46422`

## Root cause

The planned child builder still allows technical locator strings to dominate the click child target/description in the initial `plan_ready` payload.

## Fix plan

- Prefer element label / locator hint over technical locator strings for planned click/fill children.

## Verification

- Focused tests:
  - `python -m pytest tests/test_plan_model.py -q`
  - `python -m pytest tests/test_deterministic_fast_path.py -q`
- Paid E2E:
  - `python -m pytest tests/e2e/test_correction_assert_then_click_flow.py -q -s`
- Result:
  - planned click/fill children now prefer human labels from selected element context
  - correction flow initial plan review no longer falls back to `Child 1`
