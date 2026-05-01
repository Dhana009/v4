---
name: playwright-keyboard
description: Handle keyboard interactions, shortcuts, key combinations, and accessibility keyboard testing.
version: 1.0.0
metadata:
  hermes:
    tags: [keyboard, press, key, shortcut]
    category: playwright-automation
    triggers: [press, key, keyboard, shortcut,
               enter, tab, escape, ctrl, shift,
               arrow key, backspace, delete,
               key combination, hotkey]
---

# Playwright Keyboard Actions

## Single Key Press
Press key on specific element:
  Use terminal_tool to run:

  await _page.press(locator_string, "Enter")
  await _page.press(locator_string, "Tab")
  await _page.press(locator_string, "Escape")
  await _page.press(locator_string, "Backspace")
  await _page.press(locator_string, "Delete")
  await _page.press(locator_string, "ArrowDown")
  await _page.press(locator_string, "ArrowUp")
  await _page.press(locator_string, "ArrowLeft")
  await _page.press(locator_string, "ArrowRight")
  await _page.press(locator_string, "Space")
  await _page.press(locator_string, "PageDown")
  await _page.press(locator_string, "PageUp")
  await _page.press(locator_string, "Home")
  await _page.press(locator_string, "End")

## Key Combinations
Press multiple keys together:

  Ctrl+A (select all):
  await _page.press(locator_string, "Control+A")

  Ctrl+C (copy):
  await _page.press(locator_string, "Control+C")

  Ctrl+V (paste):
  await _page.press(locator_string, "Control+V")

  Ctrl+Z (undo):
  await _page.press(locator_string, "Control+Z")

  Shift+Tab (reverse tab):
  await _page.press(locator_string, "Shift+Tab")

  Ctrl+Shift+I (dev tools - avoid in tests):
  await _page.press(locator_string,
    "Control+Shift+I")

## Global Keyboard (No Element Focus)
Press key without targeting element:

  await _page.keyboard.press("Escape")
  await _page.keyboard.press("Enter")
  await _page.keyboard.press("Tab")
  await _page.keyboard.type("text to type")

## Tab Navigation Testing
Navigate through form fields with Tab:

  Focus first field:
  await _page.focus(first_field_locator)

  Tab through fields:
  await _page.press(first_field_locator, "Tab")
  await _page.press(second_field_locator, "Tab")
  await _page.press(third_field_locator, "Tab")

  Verify focus moved to expected element:
  focused = await _page.evaluate(
    "document.activeElement.getAttribute"
    "('data-testid')"
  )

## Generated Code Format

Single key:
  await page.press(
    '[data-testid="search-input"]', 'Enter')

Key combination:
  await page.press(
    '[data-testid="editor"]', 'Control+A')
  await page.press(
    '[data-testid="editor"]', 'Control+C')

Global keyboard:
  await page.keyboard.press('Escape')

Type text character by character:
  await page.keyboard.type('Hello World')

## Signal Mapping
"press Enter"              → press "Enter"
"press Tab"                → press "Tab"
"press Escape"             → press "Escape"
"press Ctrl+A"             → press "Control+A"
"press Shift+Tab"          → press "Shift+Tab"
"use arrow keys"           → press "ArrowDown"
                             or "ArrowUp"
"press Delete/Backspace"   → press key name
"keyboard shortcut [x]"    → press combination
"type text slowly"         → keyboard.type()

