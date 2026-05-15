---
name: playwright-iframe
description: Handle iframes, nested frames, shadow DOM, and out-of-process iframes.
version: 1.0.0
metadata:
  hermes:
    tags: [iframe, frame, embed, shadow]
    category: playwright-automation
    triggers: [iframe, frame, embed, nested frame,
               inside frame, shadow dom,
               web component, custom element,
               element inside iframe]
---

# Playwright Iframe Handling

## Identify If Element Is In Iframe
If locator_find returns nothing on main page:
  Check if element might be inside an iframe.
  Run dom_extract and look for iframe elements.
  If iframe found: use frame locator approach.

## Standard Iframe
Use terminal_tool to run:

  frame = _page.frame_locator(
    "iframe[name='payment']"
  )
  await frame.locator(
    element_locator
  ).click()

By iframe src:
  frame = _page.frame_locator(
    "iframe[src*='checkout']"
  )

By iframe id:
  frame = _page.frame_locator("#my-iframe")

By index (first iframe on page):
  frame = _page.frame_locator("iframe").first

## Nested Iframes
iframe inside another iframe:

  outer = _page.frame_locator(
    "iframe#outer"
  )
  inner = outer.frame_locator(
    "iframe#inner"
  )
  await inner.locator(element_locator).click()

## Shadow DOM
Element inside shadow root:

  host = _page.locator("my-component")
  shadow_input = host.locator("input")
  await shadow_input.fill("value")

Deeply nested shadow DOM:
  await _page.locator(
    "my-component >> input"
  ).fill("value")

## Generated Code Format

Standard iframe:
  const frame = page.frameLocator(
    'iframe[name="payment"]')
  await frame.locator(
    '[data-testid="card-number"]'
  ).fill('4111111111111111')

Nested:
  const inner = page
    .frameLocator('#outer')
    .frameLocator('#inner')
  await inner.locator('button').click()

Shadow DOM:
  await page.locator(
    'my-component input'
  ).fill('value')

## Signal Mapping
"element is inside iframe"   → frame_locator
"inside the frame"           → frame_locator
"shadow DOM element"         → host >> selector
"web component input"        → locator chain
"nested frame"               → chained
                               frame_locator

## Out-of-Process Iframes (OOPIF)
These are iframes from a completely different
domain. Hardest case to handle.

Example: Main page is app.example.com
         iframe src is payments.stripe.com
         These are cross-origin iframes.

Playwright handles these automatically BUT:
  - Standard frame_locator still works
  - Use the iframe src pattern to identify:
  
  frame = _page.frame_locator(
    "iframe[src*='stripe.com']"
  )
  await frame.locator(
    '[data-testid="card-number"]'
  ).fill('4111111111111111')

If frame_locator fails on OOPIF:
  Try waiting for iframe to fully load first:
  await _page.wait_for_selector(
    "iframe[src*='stripe.com']",
    state="attached"
  )
  Then use frame_locator.

## When locator_find Fails Inside Iframe
If locator_find returns nothing:
  Step 1: Check if element is in iframe
    Run dom_extract()
    Look for iframe tags in results
    
  Step 2: Identify the iframe
    Note its id, name, or src attribute
    
  Step 3: Use frame_locator directly
    frame = _page.frame_locator(
      "iframe[name='target-frame']"
    )
    
  Step 4: Run locator search inside frame
    count = await frame.locator(
      element_selector
    ).count()
    
  Step 5: Validate inside frame context
    Must get count=1 inside the frame
    Not on main page

## Common Iframe Problems and Fixes

iframe content not found:
  → Wait for iframe to load first
  → await _page.wait_for_selector(
       "iframe#target",
       state="attached"
     )
  → Then use frame_locator

Switching context accidentally:
  → Always use frame reference for
     ALL actions inside iframe
  → Never mix _page and frame locators
     for same element

Nested iframe element not found:
  → Chain frame_locator correctly:
  outer = _page.frame_locator("#outer")
  inner = outer.frame_locator("#inner")
  → Never skip a level in the chain

iframe loads slowly:
  → Add timeout to frame locator action:
  await frame.locator(selector).click(
    timeout=30000
  )
