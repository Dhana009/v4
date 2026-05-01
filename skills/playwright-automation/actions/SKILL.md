---
name: playwright-actions
description: Execute all browser actions — click, fill, select, hover, press, scroll, navigate, upload, download.
version: 1.0.0
metadata:
  hermes:
    tags: [click, fill, action, interact, type, hover]
    category: playwright-automation
    triggers: [click, fill, type, hover, press,
               select, scroll, go to, navigate,
               double click, right click, focus,
               drag, upload, download, submit]
---

# Playwright Actions

## Critical Rule — Check Before Every Action
Before executing ANY action, ask:
  Does this open a popup or dialog?
  → Register dialog handler BEFORE clicking
  
  Does this open a new tab?
  → Set up tab listener BEFORE clicking
  
  Does user want to capture network call?
  → Start network listener BEFORE action
  
  Does this need a file?
  → Check .hermes/uploads/ for the file first

## Click Actions

Standard click:
  action_click(locator=locator_string)

Click with custom timeout:
  action_click(
    locator=locator_string,
    timeout=60000
  )

Double click (use terminal_tool to run):
  await page.dblclick(locator_string)

Right click (use terminal_tool to run):
  await page.click(locator_string,
    button='right')

Hover (use terminal_tool to run):
  await page.hover(locator_string)

Focus element (use terminal_tool to run):
  await page.focus(locator_string)

## Fill and Type Actions

Fill input field:
  action_fill(
    locator=locator_string,
    value="text to fill"
  )

Fill with value from .env:
  action_fill(
    locator=locator_string,
    value="process.env.TEST_EMAIL"
  )

Fill with Faker-generated value:
  When user says "fill with any email":
  Generate: faker.internet.email()
  Tell user: "I used: generated@faker.com"

Clear field then fill:
  Use terminal_tool:
  await page.fill(locator_string, "")
  await page.fill(locator_string, new_value)

## Keyboard Actions
Press single key (use terminal_tool):
  await page.press(locator_string, "Enter")
  await page.press(locator_string, "Tab")
  await page.press(locator_string, "Escape")
  await page.press(locator_string, "Backspace")

Press key combination:
  await page.press(locator_string,
    "Control+A")
  await page.press(locator_string,
    "Control+C")

## Navigation Actions
Go to URL:
  page_navigate(url="https://example.com")
  Always waits for domcontentloaded.

Go back:
  Use terminal_tool:
  await page.go_back()

Go forward:
  Use terminal_tool:
  await page.go_forward()

Reload page:
  Use terminal_tool:
  await page.reload()

## Scroll Actions
Scroll element into view (use terminal_tool):
  await page.locator(locator_string
    ).scroll_into_view_if_needed()

Scroll to bottom of page:
  await page.evaluate(
    "window.scrollTo(0, document.body.scrollHeight)"
  )

Scroll to specific position:
  await page.evaluate(
    f"window.scrollTo(0, {y_position})"
  )

## Select Dropdown Actions

Native HTML select element:
  Use terminal_tool:
  await page.select_option(
    locator_string,
    label="Option Text"
  )
  OR:
  await page.select_option(
    locator_string,
    value="option-value"
  )

Dynamic dropdown (custom UI component):
  Step 1: Click the dropdown trigger
    action_click(locator=trigger_locator)
  Step 2: Wait for options to appear
    Use terminal_tool:
    await page.wait_for_selector(
      options_selector,
      state="visible"
    )
  Step 3: Click the desired option
    action_click(locator=option_locator)

Autocomplete / typeahead dropdown:
  Step 1: Fill search input
    action_fill(locator=input, value="search")
  Step 2: Wait for filtered results
    await page.wait_for_selector(
      results_selector,
      state="visible"
    )
  Step 3: Click matching option
    action_click(locator=option_locator)

## Upload Actions

Standard file input:
  Use terminal_tool:
  await page.set_input_files(
    locator_string,
    ".hermes/uploads/filename.pdf"
  )

Div-based upload (no file input element):
  Use file chooser API:
  async with page.expect_file_chooser() as fc:
    await page.click(upload_trigger_locator)
  file_chooser = await fc.value
  await file_chooser.set_files(
    ".hermes/uploads/filename.pdf"
  )

Wait for upload to complete:
  User says "wait up to 120 seconds":
  await page.wait_for_selector(
    confirmation_locator,
    state="visible",
    timeout=120000
  )

## Download Actions

Wait for download triggered by click:
  async with page.expect_download() as dl:
    action_click(locator=download_button)
  download = await dl.value
  await download.save_as(
    ".hermes/downloads/filename.pdf"
  )

## Popup and Dialog Actions

IMPORTANT: Register handler BEFORE the action
that triggers the popup.

Alert dialog (accept):
  page.once("dialog",
    lambda d: asyncio.ensure_future(d.accept()))
  action_click(locator=trigger_locator)

Confirm dialog (dismiss):
  page.once("dialog",
    lambda d: asyncio.ensure_future(d.dismiss()))
  action_click(locator=trigger_locator)

Prompt dialog (fill and accept):
  page.once("dialog",
    lambda d: asyncio.ensure_future(
      d.accept("input text")))
  action_click(locator=trigger_locator)

## New Tab Actions

IMPORTANT: Set up listener BEFORE the click.

Wait for new tab to open:
  async with context.expect_page() as new_page:
    action_click(locator=link_locator)
  new_tab = await new_page.value
  await new_tab.wait_for_load_state()

Work on new tab:
  title = await new_tab.title()
  url = new_tab.url

Close new tab and return:
  await new_tab.close()

## Signal Mapping — User Says → System Does
"click [element]"           → action_click
"double click [element]"    → page.dblclick
"right click [element]"     → page.click + button=right
"hover over [element]"      → page.hover
"fill [x] with [y]"         → action_fill
"type [text] in [field]"    → action_fill
"press Enter"               → page.press + Enter
"press Tab"                 → page.press + Tab
"scroll to [element]"       → scroll_into_view
"go to [url]"               → page_navigate
"select [option]"           → select_option
"upload [file]"             → set_input_files
"download [file]"           → expect_download
"a popup will open"         → register handler first
"opens a new tab"           → expect_page first
"wait up to [N] seconds"    → extract N as timeout
"observe the API call"      → start network listener

## After Every Action
1. Check result for errors
2. If success: record step
3. If error: start recovery — never crash
4. Browser stays open regardless of outcome


