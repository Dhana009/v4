---
name: playwright-scroll
description: Handle page scrolling, infinite scroll, scroll to element, and scroll inside containers.
version: 1.0.0
metadata:
  hermes:
    tags: [scroll, infinite scroll, load more]
    category: playwright-automation
    triggers: [scroll, infinite scroll, load more,
               scroll to, scroll down, scroll up,
               scroll to bottom, scroll to top,
               scroll inside, lazy load scroll]
---

# Playwright Scroll Actions

## Scroll Element Into View
Most reliable approach.
Scrolls page so element becomes visible:

  Use terminal_tool to run:
  await _page.locator(
    locator_string
  ).scroll_into_view_if_needed()

## Scroll to Bottom of Page
  await _page.evaluate(
    "window.scrollTo(0,"
    " document.body.scrollHeight)"
  )

## Scroll to Top of Page
  await _page.evaluate("window.scrollTo(0, 0)")

## Scroll to Specific Position
  await _page.evaluate(
    "window.scrollTo(0, 500)"
  )

## Scroll Inside a Container
When page has scrollable div:

  await _page.evaluate(
    """
    document.querySelector(
      '.scrollable-container'
    ).scrollTop += 300
    """
  )

## Infinite Scroll — Load More Items
Keep scrolling until all items loaded:

  previous_count = 0
  max_attempts = 10
  attempts = 0

  while attempts < max_attempts:
    current_items = await _page.locator(
      item_selector
    ).count()

    if current_items == previous_count:
      break

    previous_count = current_items
    attempts += 1

    await _page.evaluate(
      "window.scrollTo(0,"
      " document.body.scrollHeight)"
    )
    await _page.wait_for_timeout(1000)

## Scroll Then Act
Always scroll element into view before
interacting with it if it might be
outside viewport:

  await _page.locator(
    locator_string
  ).scroll_into_view_if_needed()
  await action_click(locator=locator_string)

## Generated Code Format

Scroll to element:
  await element.scrollIntoViewIfNeeded()

Scroll to bottom:
  await page.evaluate(
    'window.scrollTo(0,'
    ' document.body.scrollHeight)')

Infinite scroll:
  let previousCount = 0
  for (let i = 0; i < 10; i++) {
    const count = await page.locator(
      '.item').count()
    if (count === previousCount) break
    previousCount = count
    await page.evaluate(
      'window.scrollTo(0,'
      ' document.body.scrollHeight)')
    await page.waitForTimeout(1000)
  }

## Signal Mapping
"scroll to [element]"        → scroll_into_view
"scroll down"                → scrollTo scrollHeight
"scroll to bottom"           → scrollTo scrollHeight
"scroll to top"              → scrollTo 0,0
"load more items"            → infinite scroll loop
"scroll inside [container]"  → container.scrollTop
"element is below fold"      → scroll_into_view
                               before action

