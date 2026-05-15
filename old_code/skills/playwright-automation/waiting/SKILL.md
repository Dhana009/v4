---
name: playwright-waiting
description: All waiting strategies for dynamic content, slow pages, animations, and network activity.
version: 1.0.0
metadata:
  hermes:
    tags: [wait, loading, timeout, dynamic, slow]
    category: playwright-automation
    triggers: [wait, loading, spinner, slow,
               timeout, appear, disappear,
               dynamic, skeleton, not ready,
               takes time, load, network idle]
---

# Playwright Waiting Strategies

## Golden Rule
NEVER use sleep() or fixed delays.
Playwright auto-waits for elements to be:
  - Attached to DOM
  - Visible on screen
  - Stable (not animating)
  - Enabled (not disabled)
  - Editable (for inputs)
This happens automatically on every action.
Only add explicit waits when auto-wait is
not enough.

## When to Add Explicit Waits
- Page is a SPA that loads content after JS runs
- Network request must complete before element appears
- Animation must finish before element is stable
- User specifies a custom timeout
- Element appears/disappears based on async logic

## Wait for Element State
Use terminal_tool to run these:

Wait for element to appear (visible):
  await _page.wait_for_selector(
    locator_string,
    state="visible",
    timeout=30000
  )

Wait for element to disappear (hidden):
  await _page.wait_for_selector(
    locator_string,
    state="hidden",
    timeout=30000
  )

Wait for element to be in DOM (not visible):
  await _page.wait_for_selector(
    locator_string,
    state="attached",
    timeout=30000
  )

Wait for element to leave DOM:
  await _page.wait_for_selector(
    locator_string,
    state="detached",
    timeout=30000
  )

## Wait for Page State
Wait for page to finish loading:
  await _page.wait_for_load_state(
    "domcontentloaded"
  )

Wait for all network requests to finish:
  await _page.wait_for_load_state(
    "networkidle"
  )

Wait for full page load:
  await _page.wait_for_load_state("load")

## Wait for Navigation
Wait for page URL to change:
  await _page.wait_for_url(
    "**/dashboard**",
    timeout=30000
  )

Wait for any navigation to complete:
  Use terminal_tool:
  async with _page.expect_navigation():
    await action_click(locator=button_locator)

## Wait for Network Response
Wait for specific API call to complete:
  Use terminal_tool:
  async with _page.expect_response(
    lambda r: "/api/login" in r.url
  ) as response_info:
    await action_click(locator=submit_locator)
  response = await response_info.value

## Wait for Custom Condition
Wait for JavaScript condition to be true:
  Use terminal_tool:
  await _page.wait_for_function(
    "() => document.querySelector('.loaded')"
    " !== null"
  )

Wait for element count to change:
  await _page.wait_for_function(
    "() => document.querySelectorAll('.item')"
    ".length > 0"
  )

## User-Specified Timeouts
User says "wait up to 30 seconds":
  Extract timeout = 30000ms
  Apply to next action or assertion

User says "wait up to 2 minutes":
  Extract timeout = 120000ms

User says "this takes a long time":
  Use timeout = 60000ms as default

Always pass extracted timeout to:
  action_assert(timeout=extracted_ms)
  wait_for_selector(timeout=extracted_ms)
  action_click(timeout=extracted_ms)

## Common Scenarios

After clicking button that triggers API call:
  await _page.wait_for_load_state("networkidle")
  Then proceed with next action

After form submission that navigates:
  await _page.wait_for_url("**/success**")
  Or: await _page.wait_for_load_state("load")

After clicking button that shows modal:
  await _page.wait_for_selector(
    modal_locator,
    state="visible"
  )

After file upload (slow):
  await _page.wait_for_selector(
    confirmation_locator,
    state="visible",
    timeout=120000
  )

After infinite scroll loads more items:
  await _page.wait_for_function(
    f"() => document.querySelectorAll('{item_selector}')"
    f".length > {current_count}"
  )

After animation completes:
  await _page.wait_for_load_state(
    "domcontentloaded"
  )
  Or wait for specific stable element

## Smart Wait — Decide Which to Use
Page feels slow or content not appearing?
  → Try networkidle first
  → Then specific element wait

Element exists but action fails?
  → Element may be animating
  → Wait for domcontentloaded
  → Then retry action

Know specific element that appears when ready?
  → Always wait for that specific element
  → More reliable than generic page waits

User specifies time?
  → Use their exact timeout value
  → Never use less than what user specified

## Signal Mapping
"wait for page to load"        → networkidle
"wait for [element] to appear" → wait_for_selector
                                  state=visible
"wait for [element] to go"     → wait_for_selector
                                  state=hidden
"wait for URL to change"       → wait_for_url
"wait for API to finish"       → expect_response
"wait up to [N] seconds"       → timeout=N*1000
"this is slow"                 → timeout=60000
"takes about [N] seconds"      → timeout=N*1500


