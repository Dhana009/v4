---
name: playwright-tab
description: Handle new tabs, multiple browser tabs, tab switching, and cross-tab workflows.
version: 1.0.0
metadata:
  hermes:
    tags: [tab, window, new tab, switch]
    category: playwright-automation
    triggers: [new tab, opens tab, opens window,
               link opens, switch tab, new window,
               cross tab, multiple tabs,
               opens in new tab, target blank]
---

# Playwright Tab Handling

## Critical Rule — Set Up Listener BEFORE Click
Always set up new page listener BEFORE
clicking the link or button that opens
the new tab.

WRONG order:
  1. Click link
  2. Try to capture new tab  ← TOO LATE

CORRECT order:
  1. Set up page listener    ← FIRST
  2. Click link              ← THEN click

## Open New Tab and Work On It
Use terminal_tool to run:

  async with _context.expect_page() as new_page_info:
    await action_click(locator=link_locator)
  new_tab = await new_page_info.value
  await new_tab.wait_for_load_state(
    "domcontentloaded"
  )

Now work on new tab:
  title = await new_tab.title()
  url = new_tab.url

  Use Playwright directly on new_tab:
  await new_tab.locator(locator_string).click()
  await new_tab.locator(locator_string
    ).fill("value")

## Check New Tab URL and Title
  url = new_tab.url
  title = await new_tab.title()

  Verify URL:
  assert "expected-path" in url

  Verify title:
  assert "Expected Title" in title

## Close New Tab and Return to Original
  await new_tab.close()
  Now focus returns to original tab
  automatically.

## Switch Between Multiple Open Tabs
Get all open pages in context:
  all_pages = _context.pages
  
  First tab (original):
  original_tab = all_pages[0]
  
  Second tab (new):
  second_tab = all_pages[1]

  Switch focus to specific tab:
  await second_tab.bring_to_front()

  Switch back to original:
  await original_tab.bring_to_front()

## Run Actions on Specific Tab
After capturing new_tab reference:

  Click on new tab:
  await new_tab.locator(locator).click()

  Fill on new tab:
  await new_tab.locator(locator).fill("value")

  Assert on new tab:
  from playwright.async_api import expect
  await expect(
    new_tab.locator(locator)
  ).to_be_visible()

  Take screenshot of new tab:
  await new_tab.screenshot(
    path=".hermes/screenshots/new-tab.png"
  )

## Full Cross-Tab Workflow Example
User says: "click this link, it opens new tab,
            check title, then come back"

  Step 1: Set up listener
  async with _context.expect_page() as npi:
    await action_click(locator=link_locator)
  new_tab = await npi.value
  
  Step 2: Wait for new tab to load
  await new_tab.wait_for_load_state(
    "domcontentloaded"
  )
  
  Step 3: Check title on new tab
  title = await new_tab.title()
  
  Step 4: Assert something on new tab
  await expect(
    new_tab.locator(heading_locator)
  ).to_be_visible()
  
  Step 5: Close new tab
  await new_tab.close()
  
  Step 6: Back on original tab automatically
  Continue recording steps on original tab.

## Generated Code Format
In generated TypeScript test:

Open new tab and work:
  const [newPage] = await Promise.all([
    context.waitForEvent('page'),
    linkButton.click()
  ])
  await newPage.waitForLoadState()

Check URL and title:
  expect(newPage.url()).toContain(
    'expected-path')
  await expect(newPage).toHaveTitle(
    'Expected Title')

Work on new tab:
  await newPage.getByRole('button',
    { name: 'Submit' }).click()
  await expect(
    newPage.getByText('Success')
  ).toBeVisible()

Close and return:
  await newPage.close()

## Signal Mapping
"opens a new tab"           → context.expect_page
                              BEFORE click
"link opens in new tab"     → same as above
"target blank link"         → same as above
"switch to new tab"         → capture new_tab
                              reference
"check new tab title"       → new_tab.title()
"check new tab URL"         → new_tab.url
"close the new tab"         → new_tab.close()
"go back to original tab"   → close new tab OR
                              original_tab
                              .bring_to_front()
"work on the new tab"       → use new_tab
                              reference for
                              all actions

## Common Problems and Fixes

New tab not captured:
  → Listener was set after click
  → Move context.expect_page BEFORE click

New tab opens but empty:
  → Wait for load state after capture
  → await new_tab.wait_for_load_state()

Cannot find element on new tab:
  → Make sure using new_tab.locator()
  → Not _page.locator() which is old tab

Actions going to wrong tab:
  → Check which page reference you are using
  → Use bring_to_front() to make explicit


