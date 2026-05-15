---
name: playwright-assertions
description: Assert element and page states. All assertions auto-retry until condition met or timeout.
version: 1.0.0
metadata:
  hermes:
    tags: [assert, expect, verify, check, validate]
    category: playwright-automation
    triggers: [assert, check, verify, expect,
               should be, must be, confirm,
               visible, hidden, has text,
               wait for, ensure, validate]
---

# Playwright Assertions

## When This Skill Is Needed
Load when user wants to verify, check, assert,
or validate anything on the page.
All assertions auto-retry until condition is
met or timeout expires. Never use sleep().

## Core Assertion Tool
action_assert(
  locator=locator_string,
  assertion="visible",
  expected_value="text if needed",
  timeout=5000
)

## All Assertion Types

VISIBILITY:
  assertion="visible"
  → Element exists and is visible on page
  → Use after navigation, after clicks,
    after form submissions

  assertion="hidden"
  → Element is not visible on page
  → Use to confirm modal closed,
    error message gone, element removed

INTERACTION STATE:
  assertion="enabled"
  → Element can be clicked or typed into
  → Use before filling forms

  assertion="disabled"
  → Element cannot be interacted with
  → Use to verify inactive buttons,
    read-only fields

TEXT CONTENT:
  assertion="has_text"
  expected_value="exact text to match"
  → Element contains this exact text
  → Use to verify success messages,
    page headings, labels

  assertion="has_value"
  expected_value="value to check"
  → Input field contains this value
  → Use to verify pre-filled forms,
    confirm fill worked correctly

CHECKBOX AND RADIO:
  assertion="checked"
  → Checkbox or radio button is checked
  → Use to verify selection state

## Custom Timeout
Default timeout is 5000ms (5 seconds).
User says "wait up to 30 seconds":
  action_assert(
    locator=locator_string,
    assertion="visible",
    timeout=30000
  )

User says "wait up to 120 seconds":
  action_assert(
    locator=locator_string,
    assertion="visible",
    timeout=120000
  )

## Page-Level Assertions
For URL and title use terminal_tool to run:

Check page URL:
  from playwright.async_api import expect
  await expect(_page).to_have_url(
    "https://app.example.com/dashboard"
  )

Check URL contains pattern:
  await expect(_page).to_have_url(
    re.compile(".*dashboard.*")
  )

Check page title:
  await expect(_page).to_have_title(
    "Dashboard — My App"
  )

## Soft Assertions
Use when checking multiple things at once.
All checks run even if one fails.
Report all failures together at the end.

Use terminal_tool to run:
  from playwright.async_api import expect
  expect.soft(_page.locator(loc1)
    ).to_be_visible()
  expect.soft(_page.locator(loc2)
    ).to_have_text("expected text")
  # Hard assertion at end:
  await expect(_page).to_have_url(
    "https://..."
  )

## Element Count Assertion
Verify exactly N elements exist:
  Use terminal_tool:
  await expect(
    _page.locator(locator_string)
  ).to_have_count(3)

## Attribute Assertion
Verify element has specific attribute:
  Use terminal_tool:
  await expect(
    _page.locator(locator_string)
  ).to_have_attribute("href",
    "https://example.com")

## Class Assertion
Verify element has CSS class:
  Use terminal_tool:
  await expect(
    _page.locator(locator_string)
  ).to_have_class("active")

## Signal Mapping — User Says → Assertion Type
"assert [element] is visible"     → visible
"verify [element] appears"        → visible
"check [element] is shown"        → visible
"assert [element] is not visible" → hidden
"verify [element] disappears"     → hidden
"assert [element] is enabled"     → enabled
"assert [element] is disabled"    → disabled
"assert [element] has text [x]"   → has_text
"verify text says [x]"            → has_text
"check value is [x]"              → has_value
"verify checkbox is checked"      → checked
"assert page URL is [x]"          → to_have_url
"assert page title is [x]"        → to_have_title
"wait for [element] to appear"    → visible
                                     + high timeout
"wait for [element] to disappear" → hidden
                                     + high timeout
"wait up to [N] seconds"          → extract N
                                     as timeout ms

## Generated Code Format
In generated TypeScript test:

// Element assertions:
await expect(loginButton).toBeVisible()
await expect(errorMessage).toBeHidden()
await expect(submitButton).toBeEnabled()
await expect(emailInput).toHaveValue(
  'test@example.com')
await expect(heading).toHaveText('Dashboard')

// Page assertions:
await expect(page).toHaveURL(
  'https://app.example.com/dashboard')
await expect(page).toHaveTitle('Dashboard')

// With custom timeout:
await expect(loadingSpinner).toBeHidden(
  { timeout: 30000 })

// Soft assertions:
expect.soft(field1).toBeVisible()
expect.soft(field2).toHaveText('value')

## After Assertion
Passed: record as assertion step
Failed: start recovery flow
  Take screenshot to see current state
  Check what the element actually shows
  Verify correct locator was used
  Never crash — always recover
