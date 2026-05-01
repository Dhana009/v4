---
name: playwright-popup
description: Handle all popup types — alert, confirm, prompt dialogs and new browser windows.
version: 1.0.0
metadata:
  hermes:
    tags: [popup, dialog, alert, confirm, prompt]
    category: playwright-automation
    triggers: [popup, dialog, alert, confirm,
               prompt, modal dialog, window,
               a popup will open, opens a dialog,
               accept, dismiss, pop up]
---

# Playwright Popup and Dialog Handling

## Critical Rule — Register BEFORE Triggering
This is the most important rule for popups.
You MUST register the handler BEFORE you
click the button that opens the popup.

WRONG order:
  1. Click button
  2. Try to handle popup  ← TOO LATE

CORRECT order:
  1. Register handler     ← FIRST
  2. Click button         ← THEN click

## Types of Popups

### Type 1 — Alert Dialog
Simple message with OK button only.
User says: "click [button] — an alert will appear,
            accept it"

Use terminal_tool to run:
  import asyncio
  _page.once(
    "dialog",
    lambda d: asyncio.ensure_future(d.accept())
  )
  await action_click(locator=button_locator)

### Type 2 — Confirm Dialog
Message with OK and Cancel buttons.

Accept (click OK):
  _page.once(
    "dialog",
    lambda d: asyncio.ensure_future(d.accept())
  )
  await action_click(locator=button_locator)

Dismiss (click Cancel):
  _page.once(
    "dialog",
    lambda d: asyncio.ensure_future(d.dismiss())
  )
  await action_click(locator=button_locator)

### Type 3 — Prompt Dialog
Message with text input field and OK/Cancel.
User says: "a prompt will appear, type [text]"

  _page.once(
    "dialog",
    lambda d: asyncio.ensure_future(
      d.accept("text to type in prompt")
    )
  )
  await action_click(locator=button_locator)

### Type 4 — New Browser Window / Popup Window
A completely new browser window opens.
Different from dialog boxes.
User says: "clicking this opens a new window"

  async with _context.expect_page() as new_page_info:
    await action_click(locator=button_locator)
  new_window = await new_page_info.value
  await new_window.wait_for_load_state()

  Then work on new window:
  title = await new_window.title()
  url = new_window.url

  Close when done:
  await new_window.close()

## Reading Dialog Content
Sometimes user wants to verify dialog message.

  dialog_message = None

  async def handle_dialog(dialog):
    nonlocal dialog_message
    dialog_message = dialog.message
    await dialog.accept()

  _page.once("dialog", handle_dialog)
  await action_click(locator=trigger_locator)

  Then assert the message:
  assert "expected text" in dialog_message

## Multiple Dialogs in Sequence
If multiple dialogs appear one after another:

  dialog_count = 0

  async def handle_multiple(dialog):
    nonlocal dialog_count
    dialog_count += 1
    if dialog_count == 1:
      await dialog.accept()
    else:
      await dialog.dismiss()

  _page.on("dialog", handle_multiple)

## Generated Code Format
In generated TypeScript test:

Alert — accept:
  page.once('dialog', dialog => dialog.accept())
  await triggerButton.click()

Confirm — dismiss:
  page.once('dialog', dialog => dialog.dismiss())
  await deleteButton.click()

Prompt — fill and accept:
  page.once('dialog', async dialog => {
    await dialog.accept('input text here')
  })
  await promptButton.click()

New window:
  const [newPage] = await Promise.all([
    context.waitForEvent('page'),
    linkButton.click()
  ])
  await newPage.waitForLoadState()
  expect(newPage).toHaveURL(/expected-url/)
  await newPage.close()

## Signal Mapping
"a popup will open"         → register once handler
                              BEFORE clicking
"an alert will appear"      → dialog + accept
"confirm dialog — accept"   → dialog + accept
"confirm dialog — cancel"   → dialog + dismiss
"prompt will appear"        → dialog + accept(text)
"opens a new window"        → context.expect_page
                              BEFORE clicking
"accept the popup"          → dialog.accept()
"dismiss the popup"         → dialog.dismiss()
"close the new window"      → new_page.close()

## Common Mistake to Avoid
Never do this:
  await action_click(locator=button_locator)
  _page.once("dialog", handler)  ← wrong

Always do this:
  _page.once("dialog", handler)  ← first
  await action_click(locator=button_locator)


