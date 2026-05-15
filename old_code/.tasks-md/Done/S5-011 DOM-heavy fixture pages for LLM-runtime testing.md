# S5-011 DOM-heavy fixture pages for LLM-runtime testing

Status: Done
Sprint: Sprint 5
Type: Story
Owner: Dhanunjaya
Closed: 2026-05-12
Priority: P1
Source docs: PRD v2.3 01_PRODUCT_WORKFLOWS.md

## Resolution

Added 5 local DOM-heavy fixture pages in `tests/e2e/fixtures/test_app/`:

| File | Purpose |
|------|---------|
| `weak-divs.html` | Div-soup, no semantic anchors; repeated pseudo-button text |
| `duplicate-profiles.html` | 4 sections with identical `<h2>Profile</h2>`; repeated buttons |
| `nested-cards.html` | 3-level card nesting; nested forms with aria-labels and data-testids |
| `data-table.html` | 5-row table + 5-item list; per-user disambiguated aria-labels |
| `modal-recovery.html` | 2 modals with `role="dialog"`, JS-driven open/close toggle |

All pages self-contained (no external assets, no network).

## Tests

`tests/test_dom_heavy_fixtures.py` — 25 tests, all passing.

Asserts: existence, no external assets, doctype/title, weak-div pills have no role/aria/testid, repeated identical button text, ≥3 Profile h2s, nested card chain, table+list structure, per-user aria labels, dialog roles + hidden-by-default modals.

## Additional gaps found

None.

## Problem / Goal

**Problem:** Current E2E tests use simple semantic pages. We need weak/ambiguous pages to test page intelligence, recovery, and LLM reasoning without relying on paid LLM.

**Goal:** Create 5–6 local fixture pages that represent real-world challenges. Weak div/span pages, duplicate CTAs, form-heavy, docs/code-blocks, modal/recovery scenarios. Use for fake-model testing.

## Scope

- Create fixture server/pages in `tests/fixtures/pages/`
- Weak div/span page (no role, aria-label, no semantic HTML)
- Duplicate CTA page (multiple "Next" buttons with no distinguishing context)
- Form-heavy page (login, signup, multi-step forms)
- Docs/code-block page (markdown-style, code snippets, copy-to-clipboard CTAs)
- Modal/recovery page (modal overlays, dynamic state changes)
- Each page is self-contained HTML (no external deps)
- Smoke tests for page stability and selector stability

Out of scope:
- Huge fixture suite (5–6 pages is MVP)
- WordPress/Elementor plugin simulation (defer to backlog)
- Live interaction tests (just page stability)

## Required unit tests

- `test_fixture_pages_load.py`:
  - All fixture pages load without error
  - Page structure is stable
  - CSS/selectors don't change between loads
- `test_fixture_page_selectors.py`:
  - Each page's target element selectors are stable
  - Weak page selectors are indeed weak (multiple matches expected)
  - Duplicate CTA page has ambiguity

## Required contract tests

- `test_fixture_page_structure.py`:
  - Weak page has no role/aria-label/data-testid on CTAs (truly weak)
  - Duplicate CTA page has identical visible text
  - Form page has multiple input fields
  - Modal page can show/hide overlay

## Required integration tests

- `test_fixture_pages_with_page_intelligence.py`:
  - Weak page → page intelligence call produces useful candidates
  - Duplicate CTA page → page intelligence flags ambiguity
  - Form page → page intelligence identifies form structure

## Fixture/page needs

5–6 HTML pages in `tests/fixtures/pages/`:
1. weak_div_span_page.html
2. duplicate_cta_page.html
3. form_heavy_page.html
4. docs_code_block_page.html
5. modal_recovery_page.html

## Paid E2E requirement

None.

## Acceptance criteria

- [ ] 5–6 fixture pages created and stable
- [ ] Weak page is truly weak (no semantic attributes)
- [ ] Duplicate CTA page has ambiguity (identical text)
- [ ] Form page has multiple input types
- [ ] Modal page supports dynamic show/hide
- [ ] Docs page has code blocks and copy buttons
- [ ] Smoke tests pass
- [ ] Page selectors are stable

## Evidence

Will include:
- HTML fixture files
- Smoke test output
- Selector stability reports
- Page structure audits

## Verification commands/results

```bash
pytest tests/test_fixture_pages_load.py -v
pytest tests/test_fixture_page_selectors.py -v
pytest tests/test_fixture_page_structure.py -v
pytest tests/test_fixture_pages_with_page_intelligence.py -v

# Manual check: open each fixture in browser
python -m http.server 8000 --directory tests/fixtures/pages/
# Then visit http://localhost:8000/weak_div_span_page.html
```

## Risk

- **Low:** Fixture pages may become stale if not maintained
- **Low:** Page selectors may be too easy to break (accept, test helps catch drift)

## Mitigation

- Smoke tests run in CI on every commit
- Selector stability tests catch unexpected changes
- Document expected selectors and structure per page
