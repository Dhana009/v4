# BUG-RECORDING-003 Confirmed assertion target regressed to broad page text

Status: Done
Sprint: Sprint 3
Type: Bug
Severity: P1
Owner: Recording / Runtime
Priority: P1
Started: 2026-05-08 21:15 IST

## Source / Contract violated

- Confirmed execution contract children must preserve the specific validated target in recorded output.
- `step_recorded` and `code_update` must stay evidence-backed and specific.

## Expected

For confirmed visible assertions, the recorded child target should remain the specific confirmed target, e.g. `Playwright Test Agents`.

## Actual

`tests/test_recorded_step_model.py::test_confirmed_visible_assertion_keeps_specific_target_and_emits_code_update_when_source_text_is_broader`
failed because the recorded child target regressed to broad page text.

## Root cause

The new human-label preference added for deterministic click recordings overrode the confirmed child target too aggressively, including assertion children where the confirmed target was already the specific correct value.

## Fix plan

- Keep human-label preference for click/fill children with technical locator targets.
- Preserve specific confirmed target precedence for assertion children.

## Verification

- Focused tests:
  - `python -m pytest tests/test_recorded_step_model.py -q`
- Result:
  - confirmed assertion children keep their specific confirmed target
  - recorded output and generated code stay evidence-backed and specific
