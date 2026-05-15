# Codegen Example: Playwright.dev Hero Section (Step 1)

## Context
- **Page**: https://playwright.dev/
- **Step**: 1 (initial landing page verification)
- **Element**: Hero container `<div class="container">` inside `<header class="hero hero--primary">`

## Element Data Received

```json
{
  "tag": "div",
  "text": "Playwright enables reliable web automation for testing, scripting, and AI agents.\n\nOne API to drive ",
  "class": "container",
  "bounding_box": { "x": 0, "y": 140, "w": 905, "h": 407 },
  "parent_tag": "header",
  "scoped_html": "<header class=\"hero hero--primary heroBanner_UJJx\"><div class=\"container\"><h1 class=\"hero__title heroTitle_ohkl\"><span class=\"highlight_gXVj\">Playwright</span> enables reliable web automation for testing, scripting, and AI&nbsp;agents.</h1>..."
}
```

## Workflow Used

| Step | Tool | Input | Result |
|---|---|---|---|
| 1 | `browser_get_state` | — | URL: https://playwright.dev/, loaded |
| 2 | `locator_find` | `{class:"container", parent_tag:"header", tag:"div", text:"Playwright enables..."}` | `get_by_text("...", exact=False)` — partial text match |
| 3 | `locator_validate` | `get_by_text("Playwright enables reliable web automation", exact=False)` | valid: true, count: 1 |
| 4 | `action_assert` | locator + assertion="visible" | passed |
| 5a | `send_to_overlay` | type="step_recorded" | sent |
| 5b | `send_to_overlay` | type="code_update" | sent |

## Locator Strategy Notes
- Text contained `&nbsp;` (non-breaking space after "AI") — partial match (`exact=False`) was essential
- `get_by_text` with partial matching handled the HTML-encoded whitespace transparently
- The container had no `id`, `data-testid`, or `data-cy` attributes, ruling out those strategies
- Class-based locator would be fragile (`container` is too generic; `heroBanner_UJJx` is a CSS-module hash)

## Generated TypeScript
```typescript
await expect(page.getByText("Playwright enables reliable web automation", { exact: false })).toBeVisible();
```
