---
name: playwright-screenshot
description: Capture screenshots, visual baselines, and element-level screenshots for testing and debugging.
version: 1.0.0
metadata:
  hermes:
    tags: [screenshot, visual, capture, baseline]
    category: playwright-automation
    triggers: [screenshot, capture, take screenshot,
               visual, snapshot, baseline,
               what does page look like,
               visual test, visual diff,
               capture element, record visual]
---

# Playwright Screenshots

## Take Screenshot of Full Page
  screenshot_take(
    filename="page-name.png",
    full_page=True
  )
  Saves to: .hermes/screenshots/page-name.png

## Take Screenshot of Visible Area Only
  screenshot_take(
    filename="visible-area.png",
    full_page=False
  )

## Take Screenshot of Specific Element
  Use terminal_tool to run:
  await _page.locator(
    locator_string
  ).screenshot(
    path=".hermes/screenshots/element.png"
  )

## Screenshot on Failure — Always Do This
When any action fails:
  screenshot_take(
    filename="debug-failure.png"
  )
  Use this to understand current page state.
  Report path to user.

## Visual Baseline — Capture Once
User says "capture visual baseline for this page"

  import os
  os.makedirs(".hermes/snapshots", exist_ok=True)

  screenshot_take(
    filename="baseline-login-page.png",
    full_page=True
  )

  Save to: .hermes/snapshots/
  Tell user: "Baseline saved. Next run will
              compare against this."

## Visual Comparison in Generated Tests
In generated TypeScript test:

Full page visual test:
  await expect(page).toHaveScreenshot(
    'login-page.png',
    { maxDiffPixelRatio: 0.02 }
  )

Element visual test:
  await expect(
    page.locator('[data-testid="header"]')
  ).toHaveScreenshot('header.png')

Update baseline (when change is intentional):
  Run: npx playwright test --update-snapshots

## Screenshot File Naming Convention
Descriptive names only:
  login-page-before-submit.png
  dashboard-loaded.png
  error-state-invalid-email.png
  debug-failure-step-4.png

Never use generic names like:
  screenshot1.png
  test.png
  image.png

## Folder Structure
  .hermes/screenshots/  ← all screenshots
  .hermes/snapshots/    ← visual baselines

## Signal Mapping
"take screenshot"            → screenshot_take
"capture current state"      → screenshot_take
"what does page look like"   → screenshot_take
"visual baseline"            → screenshot + save
                               to snapshots/
"visual test"                → toHaveScreenshot
                               in generated code
"screenshot on failure"      → auto-capture on
                               any action error
"capture this element"       → element.screenshot

