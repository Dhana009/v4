---
name: playwright-dynamic
description: Handle SPAs, React/Angular/Vue apps, dynamic content, skeleton loaders, and async rendering.
version: 1.0.0
metadata:
  hermes:
    tags: [dynamic, SPA, React, Angular, loading]
    category: playwright-automation
    triggers: [SPA, React, Angular, Vue, dynamic,
               loading, skeleton, spinner,
               async content, lazy load,
               content changes, re-renders,
               after click content changes]
---

# Playwright Dynamic Content Handling

## Why Dynamic Apps Are Different
Traditional apps: page loads once, DOM is static.
SPA apps: DOM changes constantly without reload.
Content appears/disappears based on:
  - API responses
  - User interactions
  - State changes
  - Timers

## Strategy 1 — Wait for Specific Element
Best approach for dynamic content.
Wait for the exact element that proves
the content has loaded.

  await _page.wait_for_selector(
    "[data-loaded='true']",
    state="visible",
    timeout=30000
  )

  Or wait for specific text to appear:
  await _page.wait_for_selector(
    "text=Dashboard",
    state="visible",
    timeout=30000
  )

## Strategy 2 — Wait for Network Idle
After actions that trigger API calls:

  await _page.wait_for_load_state(
    "networkidle",
    timeout=30000
  )

## Strategy 3 — Wait for Element to Disappear
After loading spinner appears:
  Wait for spinner to disappear before acting.

  await _page.wait_for_selector(
    ".loading-spinner",
    state="hidden",
    timeout=30000
  )

  await _page.wait_for_selector(
    ".skeleton-loader",
    state="hidden",
    timeout=30000
  )

## Strategy 4 — Wait for DOM Change
Wait for content to update after action:

  await _page.wait_for_function(
    """() => document.querySelector(
      '.data-table'
    )?.rows.length > 1"""
  )

## Strategy 5 — Retry on Stale Element
If element reference becomes stale:
  Re-find the locator after page updates.
  Never cache locator references in SPAs.
  Always re-locate before each action.

## React Specific Patterns
Wait for React to finish rendering:
  await _page.wait_for_function(
    "() => !document.querySelector("
    "'[data-reactroot]')"
    "?.classList.contains('loading')"
  )

Wait for React state update:
  await _page.wait_for_load_state(
    "networkidle"
  )

## Angular Specific Patterns
Wait for Angular to stabilize:
  await _page.wait_for_function(
    "() => window.getAllAngularTestabilities"
    "?.().every(t => t.isStable())"
  )

## Generated Code Format

Wait for content after API call:
  await page.waitForLoadState('networkidle')
  await expect(dataTable).toBeVisible()

Wait for spinner to disappear:
  await expect(
    page.locator('.spinner')
  ).toBeHidden({ timeout: 30000 })
  await expect(content).toBeVisible()

Wait for specific element:
  await page.waitForSelector(
    '[data-testid="results"]',
    { state: 'visible', timeout: 30000 }
  )

## Signal Mapping
"page is a React app"        → use networkidle
                               after actions
"spinner appears"            → wait for hidden
"skeleton loader"            → wait for hidden
"content loads after click"  → wait_for_selector
"async data loads"           → networkidle or
                               specific element
"table updates after action" → wait_for_function
                               checking row count

## How to Detect If App Is a SPA
Before choosing wait strategy, identify app type.

Signs it IS a SPA:
  - URL changes without full page reload
  - Content updates without browser loading bar
  - React/Vue/Angular in page source
  - Single <div id="root"> or <div id="app">
    in DOM
  - Network tab shows XHR/fetch calls
    not full page loads

Check with dom_extract and browser_get_state:
  state = browser_get_state()
  If URL changes but title stays same → SPA
  If DOM updates after click without
  new page load → SPA

When SPA detected:
  ALWAYS use networkidle after actions
  NEVER rely on page load events
  ALWAYS wait for specific element
  that proves content has rendered

## What to Do When Content Never Stops Loading
Sometimes networkidle never fires because:
  Analytics keep sending requests
  Polling endpoints run every few seconds
  WebSocket connections stay active

When networkidle times out:
  Step 1: Switch strategy
    Do NOT wait for networkidle
    Instead wait for the SPECIFIC element
    that proves page is ready:
    
    await _page.wait_for_selector(
      "[data-testid='content-loaded']",
      state="visible",
      timeout=30000
    )

  Step 2: If no specific element exists
    Wait for loading indicators to hide:
    await _page.wait_for_selector(
      ".spinner, .skeleton, .loading",
      state="hidden",
      timeout=30000
    )

  Step 3: If nothing works
    Use wait_for_function with custom condition:
    await _page.wait_for_function(
      "() => document.querySelectorAll("
      "'.skeleton').length === 0 && "
      "document.querySelectorAll("
      "'.content-item').length > 0"
    )

  Step 4: Last resort
    Take screenshot to see current state
    Report to user what is happening
    Ask user to identify the element that
    proves the page is ready

## Content Keeps Re-rendering
Some React/Vue apps re-render constantly.
Element found but action fails because
component re-rendered mid-action.

Signs of this:
  "Element is detached from DOM" error
  Action works sometimes, fails sometimes
  Element found but click does nothing

Fix:
  Step 1: Wait for stable state
    await _page.wait_for_load_state(
      "networkidle"
    )
  
  Step 2: Re-find locator just before action
    Never cache locator from previous step
    Always call locator_find fresh
    
  Step 3: Use Playwright's built-in stability
    Playwright auto-waits for stable elements
    but some frameworks need extra help:
    await _page.wait_for_function(
      "() => !document.querySelector("
      "'.updating, .transitioning')"
    )
  
  Step 4: If still failing
    Use force option for click:
    await _page.locator(locator).click(
      force=True
    )
    Use only as last resort.
