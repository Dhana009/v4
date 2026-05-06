# Skill: Locator Strategy

## Purpose
Build robust Playwright locators while avoiding unnecessary LLM calls.

## When to use
Use for picker, element_info, locator_find, locator_validate, locator improvement, duplicate ambiguity, repair, replay repair, codegen locator output, Steps tab locator UI.

## Source of truth
- Complete LLM Mode locator architecture
- PRD Playwright locator guidance
- Playwright locator best practices

## Non-negotiable rules
1. Deterministic locator generation first across all modes.
2. Do not call LLM if a reliable locator validates programmatically.
3. Rank locator candidates by semantic reliability.
4. Validate live in browser when page state is correct.
5. Use scoped/chained locators for duplicates.
6. Use has/hasText/filter/container scoping before nth/index.
7. XPath/nth/index are last resort and marked fragile.
8. LLM locator suggestions are never trusted until backend validates them.
9. Locator improvement is target-specific: step_id and operation_id.
10. Live validation requires correct page_state.

## Semantic priority
Prefer:
```text
role + accessible name
label
placeholder
alt/title
stable data-testid
aria attributes
stable scoped text
stable id
scoped CSS
XPath last
```

## Required implementation behavior
- Store locator_state per step/operation.
- Store candidate_locators, selected_locator, validation_count, confidence, risk_flags, locator_scope.
- If duplicate count > 1, attempt:
  - nearest meaningful scope
  - section/card/form/dialog/table-row/list-item scope
  - ancestor heading/label relation
  - Playwright filter/has/hasText
- If user requests improvement:
  - regenerate deterministic candidates
  - validate candidates
  - only then call locator_specialist if needed or explicitly requested
- Emit locator_update_result and precondition_failed_for_locator_update.

## Required tests
- Candidate ranking tests
- Duplicate locator tests
- Scoped/chained locator tests
- Wrong-page live validation tests
- LLM fallback only when needed tests
- Fragile locator warning tests
- Replay repair locator tests where relevant

## Verification commands
```bash
python -m pytest tests/test_*locator* tests/test_*assertion* -q
```

## Stop conditions
Stop if:
- locator cannot be validated
- multiple matches remain and no disambiguation path exists
- user asked to avoid a locator style but implementation ignores it
- page state is wrong for live validation
- only fragile locator exists and no warning/user confirmation is exposed

## Reporting format
Report:
1. Locator behavior changed
2. Candidate strategy
3. Validation results
4. LLM fallback used or avoided
5. Tests/results
6. Fragility risks
