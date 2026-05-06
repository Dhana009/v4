# Skill: Real-World Fixtures and Test Data

## Purpose
Build realistic fixture pages/data so regressions reflect real product complexity, not only toy pages.

## When to use
Use when creating fixtures, E2E flows, locator tests, LLM planning tests, upload/form/result-page tests, dropdown/modal/table tests.

## Source of truth
- Real-world fixture strategy
- PRD acceptance criteria
- Frontend/LLM/backend specs

## Non-negotiable rules
1. Do not rely only on simple perfect HTML.
2. Stable CI should use captured/curated fixtures, not live sites only.
3. Live external/staging sites can be optional capture/update sources, not hard dependencies.
4. Fixtures should intentionally include weak/complex DOM.
5. Test data must be safe and redacted where needed.
6. Fixture behavior should represent real QA workflows.

## Fixture categories
Create/maintain fixtures for:
```text
Playwright-docs-like docs/code blocks
WordPress/Elementor weak DOM pages
forms and upload flows
result pages with multi-section assertions
dropdowns/static/dynamic/autocomplete
modals/popups/new tabs
tables/lists/cards
duplicate text/buttons
iframes/shadow DOM later
long-running result/wait states
```

## Required implementation behavior
- Keep fixtures deterministic.
- Include data-testid only when fixture intentionally represents good semantics.
- Include duplicate/weak locators intentionally.
- Document what each fixture validates.
- Use test-data files by reference.
- Avoid real credentials/secrets.

## Required tests
- E2E flows using realistic fixtures
- Locator ambiguity tests
- Page intelligence summary tests
- Steps/LLM planning tests
- Upload/result validation tests where relevant

## Verification commands
```bash
python -m pytest tests/e2e/<fixture_flow>.py -q -s
```

## Stop conditions
Stop if:
- fixture is too perfect to expose real bugs
- live site dependency is required for normal CI
- fixture includes sensitive data
- test does not assert product behavior
- locator ambiguity not represented where needed

## Reporting format
Report:
1. Fixture added/updated
2. Real-world behavior represented
3. Tests using it
4. Artifact paths if E2E
5. Gaps remaining
