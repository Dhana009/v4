---
name: playwright-debugging
description: Debug failing tests. Read errors, form hypothesis, apply fix, rerun. Never crash browser.
version: 1.0.0
metadata:
  hermes:
    tags: [debug, error, fix, failing, broken]
    category: playwright-automation
    triggers: [failed, error, broken, fix,
               not working, debug, timeout,
               not found, not visible,
               not interactable, crash,
               test failing, locator broken]
---

# Debugging Failed Tests

## Step 1 — Read Everything First
Before touching anything:
  1. Read full error message carefully
  2. Note exactly which step failed
  3. Take screenshot immediately:
     screenshot_take(filename="debug-state.png")
  4. Get current page state:
     browser_get_state()
  5. Form ONE hypothesis
     Never guess randomly
     Never try random fixes

## Error → Hypothesis → Fix Map

ERROR: Locator not found / count = 0
  HYPOTHESIS: Element changed or not rendered
  FIX 1: Re-run locator_find on current page
  FIX 2: Check if page navigated unexpectedly
  FIX 3: Check if element is inside iframe
  FIX 4: Wait for element then retry
  FIX 5: Scroll to element then retry

ERROR: Element not interactable
  HYPOTHESIS: Element exists but is blocked
  FIX 1: Scroll element into view first
  FIX 2: Wait for animations to complete
  FIX 3: Check if modal/overlay covers it
  FIX 4: Wait for element to be enabled
  FIX 5: Check if element is in hidden iframe

ERROR: Timeout exceeded
  HYPOTHESIS: Element taking longer than expected
  FIX 1: Add waitForLoadState networkidle before
  FIX 2: Increase timeout value
  FIX 3: Wait for specific element not generic
  FIX 4: Check network tab for slow API calls

ERROR: Strict mode violation (multiple matches)
  HYPOTHESIS: Locator matches too many elements
  FIX: Re-run locator_find with more context
       Add parent_tag and parent_id
       Use more specific attributes

ERROR: Frame detached
  HYPOTHESIS: Page navigated during action
  FIX: Wait for navigation to complete first
       Re-find element after navigation

ERROR: Navigation timeout
  HYPOTHESIS: Page load is very slow
  FIX 1: Increase navigation timeout
  FIX 2: Wait for specific element instead
  FIX 3: Use domcontentloaded not load

## Step 2 — Apply Fix
Change ONLY the specific failing part.
Never rewrite entire test for one failure.
One change at a time.
Surgical fix only.

## Step 3 — Rerun
After applying fix:
  Retry the exact failing step only.
  
  Pass: Record fix in memory.
  Update error pattern library.
  Continue test.

  Fail: New hypothesis.
  Never repeat same fix.
  Try next fix from the map above.

## Step 4 — When Genuinely Stuck
Tell user EXACTLY:
  "Failing at: Step [N] — [action description]
   Error: [exact error message]
   Current page: [URL from browser_get_state]
   Screenshot: [path from screenshot_take]
   I tried: [list every approach in order]
   I need help with: [one specific question]"

## Hard Rules During Debugging
Browser NEVER closes.
Never try same fix twice.
Always take screenshot before reporting to user.
Always check current page state first.
Never rewrite working steps to fix one step.

## Error Pattern Library
After every successful fix, save to memory:
  "When error [X] on [app]:
   Fix that worked: [description]
   Times used: 1"

Next time same error occurs:
  Check pattern library first.
  Try best known fix immediately.
  Skip strategies that failed before.

