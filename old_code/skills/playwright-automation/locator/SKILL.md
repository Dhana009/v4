---
name: playwright-locator
description: Find stable locators for any element. Programmatic waterfall first, LLM only as last resort.
version: 1.0.0
metadata:
  hermes:
    tags: [locator, selector, element, find]
    category: playwright-automation
    triggers: [find, locate, element, selector,
               locator, pick, identify, highlight]
---

# Locator Finding

## When This Skill Is Needed
Load when user wants to find, locate, or
identify any element on the page.
Also load when a locator is broken or needs
to be re-found after page changes.

## Step 1 — Collect Element Data First
Before calling locator_find, collect:
- What type of element? (button, input, link)
- What text does it show to the user?
- Does it have data-testid?
- Does it have an id?
- Does it have aria-label?
- What is its role? (button, link, textbox)
- What section of the page is it in?

## Step 2 — Call locator_find Tool
Pass everything collected:

locator_find({
  "tag": "button",
  "text": "Login",
  "id": "login-btn",
  "role": "button",
  "aria_label": "Login to your account",
  "data_testid": "login-button",
  "placeholder": "",
  "parent_tag": "form",
  "parent_id": "login-form"
})

Include as much data as available.
More data = better locator found.

## Step 3 — Read the Result

If found=true AND stable=true:
  Perfect locator found.
  Proceed to validation.

If found=true AND stable=false:
  Fragile locator found (XPath or CSS class).
  Still usable but show warning:
  "⚠ This locator may break when page changes.
   Ask developer to add data-testid."
  Add comment in generated code.

If found=false:
  No locator found programmatically.
  Try with more context:
    Add parent_tag and parent_id
    Try different text variation
  If still not found: use LLM assistance.

## Step 4 — Always Validate After Finding
Call locator_validate immediately:

locator_validate(locator="found_locator_string")

Result must be:
  valid=true AND count=1

If count=0:
  Element not present on current page.
  Check if page needs to scroll.
  Check if element is in an iframe.
  Check if element appears after interaction.

If count>1:
  Locator is not unique.
  Add more context to element_data.
  Re-run locator_find.
  Keep refining until count=1.

If count=1:
  Locator confirmed. Record it.

## Multiple Matches — How to Make Unique
If locator finds 2+ elements, try:

Option 1: Add parent context
  "parent_tag": "form",
  "parent_id": "login-form"

Option 2: Combine attributes
  Use data-testid if available
  Combine role + exact text + parent

Option 3: Add position context
  Which instance is it? First? Second?
  "nth": 0

Never stop until exactly 1 element found.

## Locator Stability Reference

MOST STABLE — Use first:
  data-testid="login-btn"        → best
  data-cy="submit-button"        → best
  aria-label="Close dialog"      → very good
  role=button name="Login"       → very good
  id="email-input"               → good
  placeholder="Enter email"      → good

LESS STABLE — Use as fallback:
  Exact text match               → ok
  Partial text match             → ok
  CSS .classname                 → fragile
  XPath //button[@class="..."]   → fragile

ALWAYS WARN USER when using fragile locator.

## Persistent Locator Library
After finding a validated locator, save it:

.hermes/locators/[app-domain].json

Next session for same app:
  Check library first before running waterfall
  Reuse confirmed stable locators
  Update library when locator breaks

## When LLM Help Is Needed
ONLY when all 14 programmatic strategies fail.
Send to LLM:
  - Element data (focused, small)
  - List of strategies already tried
  - Immediate parent + siblings only
  - Current page URL

NEVER send:
  - Full page DOM
  - Full accessibility tree
  - Unrelated page sections

After LLM suggests a locator:
  Always validate with locator_validate
  Must get count=1 before using


