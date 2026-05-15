---
name: playwright-assertions-compact
description: Compact assertion rules. Use for simple flows.
version: 1.0.0
---

# Assertions (Compact)

## Tool
action_assert(locator=locator_string, assertion="visible", expected_value="text if needed", timeout=5000)

## Assertion Types
- visible / hidden — element visibility
- enabled / disabled — interaction state
- has_text — element contains exact text (set expected_value)
- has_value — input contains value (set expected_value)
- checked — checkbox/radio is checked

## Rules
- All assertions auto-retry until met or timeout
- Never use sleep() — use timeout parameter instead
- Default timeout: 5000ms
