# Codegen Example: Playwright.dev Hero Section (Step 2)

## Context
- **Page**: https://playwright.dev/
- **Step**: 2 (container visibility assertion)
- **Element**: Div container inside header hero section

## Element Data Received

```json
{
  "tag": "div",
  "text": "Playwright enables reliable web automation for testing, scripting, and AI\u00a0agents.\n\nOne API to drive ",
  "id": "",
  "role": "",
  "aria_label": "",
  "data_testid": "",
  "data_cy": "",
  "data_qa": "",
  "placeholder": "",
  "name": "",
  "type": "",
  "class": "container",
  "href": "",
  "value": "",
  "bounding_box": { "x": 0, "y": 140, "w": 905, "h": 407 },
  "parent_tag": "header",
  "parent_id": "",
  "scoped_html": "<header class=\"hero hero--primary heroBanner_UJJx\"><div class=\"container\"><h1 class=\"hero__title heroTitle_ohkl\"><span class=\"highlight_gXVj\">Playwright</span> enables reliable web automation for testing, scripting, and AI&nbsp;agents.</h1><p class=\"heroSubtitle_GKHc\">One API to drive Chromium, Firefox, and WebKit \u2014 in your tests, your scripts, and your agent workflows. Available for<!-- --> <a href=\"https://playwright.dev/docs/intro\">TypeScript</a>,<!-- --> <a href=\"https://playwright.dev/python/docs/intro\">Python</a>,<!-- --> <a href=\"https://playwright.dev/dotnet/docs/intro\">.NET</a>, and<!-- --> <a href=\"https://playwright.dev/java/docs/intro\">Java</a>.</p><div class=\"buttons_pzbO\"><a class=\"getStarted_Sjon\" href=\"/docs/intro\">Get started</a><span class=\"github-btn github-stargazers github-btn-large\"><a class=\"gh-btn\" href=\"https://github.com/microsoft/playwright\" rel=\"noopener noreferrer\" target=\"_blank\" aria-label=\"Star microsoft/playwright on GitHub\"><span class=\"gh-ico\" aria-hidden=\"true\"></span><span class=\"gh-text\">Star</span></a><a class=\"gh-count\" href=\"https://github.com/microsoft/playwright/stargazers\" rel=\"noopener noreferrer\" target=\"_blank\" aria-label=\"86k+ stargazers on GitHub\" style=\"display:block\">86k+</a></span></div></div></header>"
}
```

## Locator Nuance: Child vs Container

This step demonstrates an important nuance:

1. **`locator_find` returned `get_by_text(...)`** matching the h1 text inside the container
2. This locator actually targets the **child `<h1>`**, not the **container `<div>`**
3. **Action**: Manually crafted a structural CSS selector `header .container` instead
4. **Validation**: `locator_validate("header .container")` → valid, count: 1
5. **Assertion**: Used `action_assert` with `assertion="visible"` on the structural locator

**Rule of thumb**: When the target element is a layout container (`<div>`, `<section>`, `<header>`, `<main>`) and `locator_find` returns a text-based strategy, it's almost certainly pointing to a child element. Pivot to a structural CSS selector validated against the page.

## Workflow Used

| Step | Tool | Input | Result |
|---|---|---|---|
| 1 | `locator_find` | `{tag:"div", class:"container", parent_tag:"header", text:"Playwright enables..."}` | `get_by_text(..., exact=True)` — child-targeting |
| 2 | *(manual)* | Crafted `header .container` | — |
| 3 | `locator_validate` | `header .container` | valid: true, count: 1 |
| 4 | `action_assert` | locator + assertion="visible" | passed |
| 5a | `send_to_overlay` | type="step_recorded" | sent |
| 5b | `send_to_overlay` | type="code_update" | sent |

## Why Structural CSS Worked

- `header` — unique parent tag (only one hero header on the page)
- `.container` — specific class within that context
- Combined `header .container` resolved to exactly 1 element
- No fragile CSS-module hashes (like `heroBanner_UJJx`) required

## Generated TypeScript

```typescript
await expect(page.locator('header .container')).toBeVisible();
```
