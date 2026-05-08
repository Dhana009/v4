---
name: playwright-actions-compact
description: Compact action rules — click, fill, navigate. Use for simple flows.
version: 1.0.0
---

# Actions (Compact)

## Click
action_click(locator=locator_string)
Before clicking: check if action opens popup/dialog/tab — register handler first if so.

## Fill
action_fill(locator=locator_string, value="text")
For .env values: value="process.env.VAR_NAME"

## Navigate
page_navigate(url="https://...")

## Key Rules
- Validate locator resolves to exactly 1 element before any action
- Never execute action before user confirms plan_ready
