# Intent-to-Plan Example: Playwright.dev Hero Section (Assert + Click)

## Context
- **Page**: https://playwright.dev/
- **Intent**: "assert the text and click the button"
- **Selected element**: `<div class="container">` containing hero text — a structural container, not an interactive element

## Key Challenge
The selected element was a container `div`, but the user wanted to:
1. Assert text visible in the container
2. Click a button (somewhere inside or elsewhere on the page)

The button target was ambiguous because the container itself is not clickable.

## Workflow Used

### Phase 1: Analysis
- Identified the selected element is a `<div>` container with text content
- Recognized the intent has **two distinct actions** (assert + click) targeting **different elements**
- The click target was ambiguous — container had no `href`, no `role="button"`

### Phase 2: Inspect Container
Called `dom_extract(scope="div.container")` — found 7 links inside:
- "TypeScript" → /docs/intro
- "Python" → /python/docs/intro
- ".NET" → /dotnet/docs/intro
- "Java" → /java/docs/intro
- **"Get started"** → /docs/intro (class `getStarted_Sjon`) — primary CTA
- "Star" → GitHub repo
- "86k+" → stargazers

### Phase 3: Clarification
Sent `clarification_needed` with question: "The selected element is a container div with text. Which button would you like to click?"
Options: button inside container, different button, or inspect contents.
User replied: "click this" — confirming the button is inside the container.

### Phase 4: Plan Generation
Sent `plan_ready` with two steps:

| Step | Action | Locator Strategy | TypeScript |
|------|--------|-----------------|------------|
| 1 | Assert text visible | `getByText('Playwright enables reliable...')` | `await expect(page.getByText('Playwright enables reliable web automation for testing, scraping and more.')).toBeVisible();` |
| 2 | Click "Get started" | `getByRole('link', { name: 'Get started' })` | `await page.getByRole('link', { name: 'Get started' }).click();` |

### Locator Decisions
- **Text assertion**: Used `getByText` with partial match to handle any HTML-encoded characters. The text "scraping and more." was the identifying substring.
- **Button click**: Used `getByRole('link', { name: 'Get started' })` — accessible, robust, independent of CSS class names that might change. The `a.getStarted_Sjon` class could be a CSS-module hash, so role-based was safer.

## Key Takeaways
1. **Container → inspect first** — When selected element is a structural tag, use `dom_extract` before asking the user
2. **Separate locators per action** — Assert text uses the container's text; clicking uses the child button. Never try to find one locator for both.
3. **Prefer `getByRole` for interactive elements** — More robust than CSS classes for buttons/links, since it tests by semantics, not styling
4. **Partial text with `getByText`** — Avoids false negatives from `&nbsp;`, whitespace variants, or truncated text in the selection output
5. **Plan before executing** — Present the full multi-step plan and let the user confirm with `/go` before running any actions
