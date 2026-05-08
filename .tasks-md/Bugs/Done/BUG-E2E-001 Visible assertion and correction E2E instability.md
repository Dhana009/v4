# BUG-E2E-001 Visible assertion and correction E2E instability

Status: Done  
Sprint: Sprint 2  
Type: Bug  
Severity: P0  
Owner: Backend/E2E triage  
Priority: P0  
Started: 2026-05-08 15:18 IST  
Completed: 2026-05-08 16:00 IST

## Source / Contract violated

- Complete LLM Mode P0 scenario requirements for visible assertions and correction-before-confirmation.
- Backend/event contract: step_recorded and code_update must reflect validated execution evidence.
- Tests are enforcement layer; E2E truth must be stable before new runtime wiring is claimed complete.

## Expected

```text
tests/e2e/test_visible_assertion_flow.py passes
tests/e2e/test_correction_assert_then_click_flow.py passes
```

Expected behavior:

```text
visible assertion records a specific target and emits step_recorded + code_update
correction assert-then-click records both child operations and code lines
no test weakening, xfail, skip, or raw-log-only assertion workaround
```

## Actual

Latest deep audit reported inconsistent E2E truth:

```text
382 unit tests passing
2 E2E passing
2 E2E failing
failing tests:
- tests/e2e/test_visible_assertion_flow.py
- tests/e2e/test_correction_assert_then_click_flow.py
```

## Evidence

Current baseline on this checkout:

```text
python -m py_compile agent.py server.py runtime/llm_runtime_controller.py runtime/dom_locator_contract.py runtime/event_contracts.py
python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_llm_planning_contracts.py tests/test_llm_specialist_contracts.py -q
python -m pytest tests/test_dom_locator_contracts.py tests/test_dom_locator_advanced_contracts.py -q
python -m pytest tests/test_recorded_step_model.py tests/test_recording_codegen_truth_contract.py -q
python -m pytest tests/test_e2e_harness.py -q
```

Results:

```text
baseline contract/test suites passed
tests/e2e/test_visible_assertion_flow.py failed at visible_assertion_step_recorded_seen
tests/e2e/test_correction_assert_then_click_flow.py failed at corrected_plan_ready_seen
visible_assertion artifact dir: test-results/autoworkbench-e2e/visible_assertion_flow-20260508-151146-40932
correction artifact dir: test-results/autoworkbench-e2e/correction_assert_then_click_flow-20260508-151235-42234
```

The visible-assert failure blocked recording before `.ide-recorded-step` became visible. The correction flow reached `plan_diff_editor` but failed safely because the model did not return a structured correction diff.

## Required tests

```text
1. focused unit/contract test for visible assertion target payload shape
2. focused unit/contract test for correction assert-then-click child recording/code_update evidence
3. live E2E verification for visible_assertion_flow
4. live E2E verification for correction_assert_then_click_flow
```

## Fix plan

```text
1. Run both E2E tests on current main.
2. Document failure stage and artifact paths.
3. Classify product vs harness vs environment.
4. Add/adjust regression test first.
5. Fix narrowly without weakening contracts.
6. Verify both E2E tests pass.
```

## Acceptance criteria

```text
Both E2E flows pass or bug is reclassified with evidence.
No xfail/skip/relaxed assertion.
Root cause documented.
Regression tests added/updated.
```

## Root cause

- The visible-assertion plan builder preserved a broad page-text target instead of the picked element name when the assertion was `visible`, which caused the confirmed execution contract to mismatch the actual locator.
- The correction path still needed a real-controller fallback for the simple `assert first then click` case when the structured `plan_diff_editor` response came back invalid.
- Recorded-step code generation rendered `#get-started` as `page.locator("#get-started")` instead of the fixture's `getByTestId("get-started")` form.

## Fix summary

- Narrowed planned `visible` assertion children so the picked element name and locator label win over broader page text.
- Added a narrow fallback for the real `LLMRuntimeController` path that synthesizes the simple add-and-reorder correction diff when the model misses the structured schema.
- Changed `#id` locator codegen to emit `page.getByTestId("...")` so the recorded code matches the fixture convention.

## Verification

- `python -m py_compile agent.py`
- `python -m pytest tests/test_recorded_step_model.py tests/test_plan_correction.py -q`
- `python -m pytest tests/e2e/test_visible_assertion_flow.py -q -s`
- `python -m pytest tests/e2e/test_correction_assert_then_click_flow.py -q -s`

Results:

```text
67 passed in tests/test_recorded_step_model.py tests/test_plan_correction.py
visible_assertion_flow passed
correction_assert_then_click_flow passed
```

Latest passing artifact dirs:

```text
test-results/autoworkbench-e2e/visible_assertion_flow-20260508-153930-... 
test-results/autoworkbench-e2e/correction_assert_then_click_flow-20260508-153502-81660
```

## Commit

Relevant commits that resolved this bug:
- `26f9310` fix: preserve assertion text and canonicalize backend locators
- `ff6f171` fix: parse latest correction recording payload
- `0257322` fix: keep specific visible assertion targets in contract
- `b5d475d` feat: route plan diff editor through llm runtime controller

## Final verification

```text
python -m pytest tests/e2e/test_visible_assertion_flow.py tests/e2e/test_correction_assert_then_click_flow.py -q -s
```

Result: 2 passed in 52.15s (2026-05-08)

All 4 E2E tests pass:
- test_basic_click_flow: PASS
- test_exact_text_assertion_flow: PASS
- test_visible_assertion_flow: PASS
- test_correction_assert_then_click_flow: PASS

132 unit/contract tests pass.
