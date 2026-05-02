# 02 — LLM Runtime

## v2.3 note — Multi-model orchestration pointer

The LLM Runtime starts with one main model for MVP, but the stabilized architecture supports multiple model-backed specialist agents. Detailed scope, triggers, out-of-scope boundaries, UI controls, and expected outcomes are defined in `07_MULTI_MODEL_ORCHESTRATION.md`.

Summary:

```text
Main Orchestrator Agent = user intent, planning, coordination
Page Intelligence / Locator Agent = cheap/nano DOM/page understanding and locator candidates
Debug Agent = failure diagnosis and recovery proposals
Codegen Reviewer Agent = optional review of deterministic codegen output
Step Runner = source of truth, execution, validation, recording
```

Non-negotiable rule: sub-agents do not execute Playwright actions, record steps, or decide finality. They produce structured suggestions; Step Runner validates truth.

### Expected criteria

- LLM Runtime can operate with one main model for MVP.
- Architecture remains pluggable for Page Intelligence, Debug, and Codegen Reviewer agents.
- Model calls are routed by purpose, risk, cost, and context size.
- Optional agent failures degrade gracefully to deterministic extraction and/or the main model.


> PRD v2.3 modular pack. Existing PRD v2.2 wording is preserved where it still applies. New or corrected material is marked as v2.3 guidance.


## v2.3 LLM runtime clarification

The LLM layer must support three scales of work:

```text
Small: one selected element → one action/assertion
Medium: selected section → parent step with multiple child operations
Large: full page/flow exploration → proposed plan, confirmed execution, recording, replay repair
```

The LLM is the reasoning engine, not the lifecycle authority. Step Runner, Tool Runtime, Context Manager, Recovery Manager, Recorder, Codegen, and Gap Logger are separate responsibilities.

## Runtime ownership

| Component | Owns |
|---|---|
| Step Runner | step lifecycle, status, finality, recorded/skipped truth |
| Context Manager | prompt context, DOM mode, history compaction, token budget |
| Tool Runtime | safe Playwright execution and tool preconditions |
| Recovery Manager | deterministic recovery, LLM repair attempts, user escalation |
| Recorder | parent step + child operation persistence |
| Codegen | valid Playwright TypeScript output |
| Gap Logger | unsupported/missing capability records |
| LLM | intent interpretation, decomposition, planning, explanation, repair suggestions |

## LLM failure modes to guard

| Risk | Guard |
|---|---|
| LLM does too much for broad intent | plan proposal with grouped child operations and confirmation |
| LLM reorders user intent incorrectly | preserve user order unless explicitly justified and confirmed |
| DOM becomes stale after navigation | DOM versioning and revalidation after mutating actions |
| LLM loops repeatedly in recovery | deterministic and LLM retry limits before user escalation |
| LLM gives up too early | show tried fixes and ask one precise question |
| LLM records weak locator | score, warn, preserve alternatives, allow locator update |
| LLM generates invalid TS | backend codegen converts runtime locators to TypeScript |
| LLM changes goal during recovery | recovery anchored to original failed step |
| Missing tool/capability | explain, record gap, continue supported parts |
| Destructive action | extra explicit confirmation |

## Capability gap logging

If user intent cannot be completed because the runtime lacks a tool, handler, or supported workflow, the system records a capability gap under the active workspace.

Example location:

```text
<workspace>/.autoworkbench/gaps/capability-gaps.jsonl
```

Example entry:

```json
{
  "timestamp": "2026-05-02T00:00:00+05:30",
  "url": "https://example.com/reports",
  "user_intent": "download the report and verify file content",
  "failed_step_id": "step_4",
  "reason": "missing_tool",
  "needed_capability": "download file content verification",
  "available_tools": ["click", "fill", "assert", "page_go_back"],
  "suggested_future_work": "Add first-class download verification tool"
}
```

### Expected criteria

- Unsupported work is not silently ignored or faked.
- A gap entry is written only when the limitation is real and actionable.
- Gap logging never stores secrets, tokens, or private input values.


## Retry and escalation policy

Default policy:

```text
per failed child operation:
  deterministic recovery attempts: max 2–3
  LLM repair attempts: max 2
  then ask user one specific question
```

The exact numbers may be configurable, but unlimited loops are not allowed.

### Expected criteria

- Repeated failures stop escalating token cost indefinitely.
- User receives a concise summary of tried fixes before being asked.
- Recovery remains attached to the original failed step/operation.


---

> **Preserved v2.2 reference only.** If this section conflicts with v2.3 guidance above, v2.3 wins.

## Preserved v2.2 runtime sections

### The core principle

**Measure first. Decide after. Never send more than needed.**

The token strategy is adaptive — it changes based on what the user selected, current step risk, page complexity, and failure count. The goal is **not** to minimize tokens blindly. The goal is to send the smallest context that can safely preserve decision quality.

### DOM context modes

The Context Manager chooses one of four modes for each LLM call:

| Mode | When used | Context included | Goal |
|---|---|---|---|
| Normal | Most picked-element actions/assertions | selected element descriptor, nearby context, current URL/title, step state, known locator candidates | Lowest cost while preserving accuracy |
| Explore | Page/section is unknown or user asks to understand page | landmarks, headings, forms, buttons, links, tables, dialogs, page map summary | Build structured understanding without raw full DOM |
| Debug | A locator/action/assertion failed or repeated retries happened | failed step, failed locator, tried strategies, current focused DOM, actual text, screenshot path, current URL/title | Explain and recover without losing quality |
| Full DOM fallback | Focused/explore/debug modes fail, or user explicitly asks | capped raw DOM or cleaned HTML with truncation warnings | Last-resort diagnosis |

Escalation is allowed. Blind dumping is not. A full DOM fallback must be logged with the reason it was needed.

The token strategy is adaptive — it changes based on what the user selected and how big the DOM is.

### Three selection scenarios

#### Scenario A — Single element selected

User clicked one specific element.

```
Extract element descriptor:
  tag, id, name, type, role, aria-label,
  placeholder, data-testid, data-cy, data-qa,
  text content (truncated to 50 chars),
  class list (top 3 most specific),
  parent: { tag, id, role } (1 level only),
  siblings: [{ tag, text, id }] (max 3)

Token cost: ~200-400 tokens
LLM involvement: only if programmatic waterfall fails
```

This is ~80% of all interactions. Cheap and fast.

#### Scenario B — Section selected

User selected a form, nav bar, table, card, or any container.

```
STEP 1: Try accessibility tree first
  Playwright: await page.accessibility.snapshot({root: element})
  
  Good semantic markup?
    YES → structured tree is clean, already compressed
          Typically 500-2000 tokens
          Send directly
    
    NO (div soup)?
          Fall through to STEP 2

STEP 2: Extract and clean the HTML
  Get element.outerHTML
  Strip: style attributes, script tags,
         comments, SVG paths,
         data-* attributes (keep testid/cy/qa only),
         class lists > 3 classes
  
  Measure token count:
  
  < 2000 tokens  → send cleaned HTML directly
  
  2000-5000 tokens → extract interactive elements only:
    All: button, input, select, textarea, a[href]
    All: [role=button], [role=link], [role=checkbox]
    All: [data-testid], [aria-label]
    With their key attributes only
    Typical result: 500-1500 tokens
  
  > 5000 tokens → ask user ONE question:
    "This section is large. What specifically
     are you trying to do here?"
    User narrows scope → start over with smaller selection
```

#### Scenario C — Full page selected

User wants to explore or understand the entire page.

```
FIRST CHECK: Do we have a fresh page map?
  .hermes/page-maps/[domain]/[path].json
  
  EXISTS and < 24 hours old:
    Load summary section (~300 tokens)
    Inject into context
    Zero exploration cost — LLM already knows this page
  
  DOES NOT EXIST or STALE:
    Run phased exploration:
    
    PHASE 1 — Structure only (1 LLM call)
      page.accessibility.snapshot() at depth 2
      LLM identifies: sections, regions, counts
      ~300-600 tokens input
      
    PHASE 2 — Interactive elements per section (1 LLM call per section)
      For each section from Phase 1:
      Extract only interactive elements
      ~500-1000 tokens per section
      
    PHASE 3 — Hidden DOM (only if user asks)
      Click expandable elements (dropdowns, accordions, modals)
      Capture revealed DOM
      Go back
      Add to map
    
    SAVE: .hermes/page-maps/[domain]/[path].json
    {
      "url": "...",
      "explored_at": "ISO timestamp",
      "sections": { ... },
      "interactive_elements": { ... },
      "hidden_reveals": { ... },
      "summary": "plain English description"
    }
    
    NEXT VISIT: Load from file. 0 exploration cost.
```

### Div soup handling

When an element has no semantic attributes (no id, no role, no aria-label, no data-testid):

```
Strategy 1: Visual context
  element.getBoundingClientRect()
  → position on page, size
  → "element in top-right region, 80x36px"

Strategy 2: Text content + parent text
  element.innerText (max 100 chars)
  parent.innerText (max 200 chars)
  → LLM builds getByText() or CSS based on this

Strategy 3: Screenshot of element region (vision model)
  page.screenshot({ clip: boundingBox })
  Send image to LLM
  LLM identifies element visually
  LLM suggests best locator from visual context

Strategy 4: Confirm with user before fragile fallback
  If none of the above yields a stable locator:
  "I cannot find a stable locator for this element.
   The page has no semantic attributes here.
   Options:
   [1] Ask your developer to add data-testid
   [2] Use this XPath (fragile): [xpath]
   [3] Use this JS expression (fragile): [js]
   [4] Skip this step"
  User chooses → system proceeds accordingly
```

### Token budget summary

| Selection | Markup | Strategy | Max tokens sent |
|---|---|---|---|
| Single element | Any | Descriptor only | 400 |
| Section | Good semantics | Accessibility tree | 2000 |
| Section | Div soup | Interactive elements only | 1500 |
| Section | Very large | Ask user to narrow | 0 (blocked) |
| Full page | First visit | Phased exploration | 4000 total |
| Full page | Revisit | Load page map | 300 |
| Full page | Stale | Re-explore changed sections | 1500 |

---

### Locator priority waterfall

Every locator attempt follows this exact order. Programmatic first. LLM only when all programmatic strategies fail.

```
PROGRAMMATIC LAYER — zero LLM cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Test attributes (most stable)
   data-testid, data-cy, data-qa,
   data-test, data-automation-id

2. Semantic/ARIA locators
   aria-label, aria-role,
   role + name combination,
   aria-placeholder, aria-describedby

3. Native attributes
   id (unique), name attribute,
   type + value combination

4. Text content
   Exact text match
   Partial text match (getByText with exact:false)

5. Label association
   getByLabel() — input associated with label element

6. Placeholder text
   getByPlaceholder()

7. Alt text
   getByAltText() — images

8. CSS selectors
   Stable class combinations
   Attribute selectors
   Avoid: dynamic classes, position-based

LLM LAYER — only if all 8 programmatic strategies fail
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. LLM receives focused element snapshot only
   Knows complete history of what failed
   Never repeats a failed strategy
   Can suggest any strategy not yet tried
   Gets smarter with every retry

LAST RESORT — only after LLM exhausts all options
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10. XPath (relative or absolute) — only if LLM recommends it
    Never proactively generated
    Always flagged as fragile in output
    Code comment: ⚠ Fragile — consider adding data-testid

11. JavaScript injection — only if LLM recommends it
    Custom JS to find element any other way
    LLM writes the expression
    User is asked to confirm before this is used:
    "I could only find this element using a JavaScript
     expression. This is fragile. Shall I use it?"
    User confirms → recorded with fragile warning
    User declines → step is skipped or manually handled
```

### Validation rule — non-negotiable

Every locator must resolve to **exactly 1 element**:

```
Finds 0 → not found → try next strategy
Finds 2+ → not unique → add more context (parent, sibling, position) → retry
Finds 1 → validated ✅ → record step
```

System never gives up on uniqueness. It keeps refining until exactly 1 element matches, or genuinely exhausts all options.

### Locator stability scoring

Every locator candidate gets a confidence score:

| Strategy | Stability | Score | When used |
|---|---|---|---|
| data-testid | Highest | 100 | Always first |
| aria-label + role | High | 90 | Always |
| id attribute | High | 85 | Always |
| getByLabel | High | 82 | Always |
| Exact text | Medium-High | 75 | Always |
| CSS (stable classes) | Medium | 60 | Always |
| XPath (any form) | Low | 20 | Only if LLM recommends + user confirms |
| JS injection | Variable | 15 | Only if LLM recommends + user confirms |

**Fragile locator warning:**  
If the best available locator scores below 60, or if XPath/JS injection is used:
- Warning symbol shown in step panel
- Comment added to generated code:
  ```typescript
  // ⚠ Fragile locator — no stable attributes found
  // Consider adding data-testid to this element
  const submitBtn = page.locator('//form/div[3]/button')
  ```
- Non-blocking — flow continues. User is informed, not stopped.

---

All of these must be supported in both Manual mode (dropdown selection) and LLM mode (described in natural language).

### Navigation

```typescript
await page.goto(url)
await page.goBack()
await page.goForward()
await page.reload()
```

### Click & Pointer

```typescript
await locator.click()
await locator.dblclick()
await locator.hover()
await locator.focus()
await locator.blur()
await page.mouse.click(x, y)                      // coordinate click
await locator.click({ button: 'right' })           // right click
await locator.click({ modifiers: ['Shift'] })      // shift click
await locator.dragTo(target)                       // drag and drop
```

### Keyboard & Input

```typescript
await locator.fill(value)                          // clear + type
await locator.clear()
await locator.type(value)                          // char by char (special cases)
await locator.pressSequentially(value)             // triggers key events
await locator.press('Enter')
await locator.press('Tab')
await locator.press('Escape')
await locator.press('Control+A')
await page.keyboard.press(key)
await page.keyboard.type(text)
```

### Select & Dropdown

```typescript
// Native <select>
await locator.selectOption(value)
await locator.selectOption({ label: 'Option text' })
await locator.selectOption({ index: 2 })

// Dynamic dropdown (SPA/React/Angular)
await trigger.click()
await page.waitForSelector(optionsSelector)
await option.click()

// Search/typeahead dropdown
await searchInput.fill(searchText)
await page.waitForSelector(filteredOptionsSelector)
await option.click()
```

### Checkboxes & Radio Buttons

```typescript
await locator.check()
await locator.uncheck()
await locator.setChecked(true/false)
expect(locator).toBeChecked()
```

### File Upload

```typescript
// Standard file input
await locator.setInputFiles(filePath)
await locator.setInputFiles([file1, file2])         // multiple files

// Div-based upload (file chooser triggered by click)
const [fileChooser] = await Promise.all([
  page.waitForEvent('filechooser'),
  locator.click()
])
await fileChooser.setFiles(filePath)

// Drag and drop file
await page.dragAndDrop(sourceSelector, targetSelector)
```

### New Tab Handling

```typescript
// MUST set up BEFORE the click that triggers the new tab
const [newPage] = await Promise.all([
  page.context().waitForEvent('page'),
  locator.click()
])
await newPage.waitForLoadState()
// Now work on newPage
```

### Popup & Dialog Handling

```typescript
// MUST register BEFORE the action that triggers the dialog
page.on('dialog', async dialog => {
  await dialog.accept()                             // or dismiss()
  await dialog.accept(promptText)                  // for prompt dialogs
})
// Then trigger the action
await locator.click()
```

### iFrame Handling

```typescript
// Single iframe
const frame = page.frameLocator(iframeSelector)
await frame.locator(elementSelector).click()

// Nested iframes (depth-first)
const outerFrame = page.frameLocator(outerIframeSelector)
const innerFrame = outerFrame.frameLocator(innerIframeSelector)
await innerFrame.locator(elementSelector).fill(value)
```

### Scroll

```typescript
await locator.scrollIntoViewIfNeeded()
await page.mouse.wheel(0, deltaY)
await page.evaluate(() => window.scrollTo(x, y))
await page.keyboard.press('End')                   // scroll to bottom
await locator.hover()                              // triggers scroll to element
```

### Wait Strategies

```typescript
// Never use page.waitForTimeout() — it is an arbitrary sleep
// Always use condition-based waits:

await page.waitForSelector(selector, { state: 'visible' })
await page.waitForSelector(selector, { state: 'hidden' })
await page.waitForSelector(selector, { state: 'attached' })
await page.waitForSelector(selector, { state: 'detached' })

await locator.waitFor({ state: 'visible' })
await locator.waitFor({ state: 'hidden' })

await page.waitForURL(urlPattern)
await page.waitForURL(urlPattern, { timeout: 10000 })

await page.waitForLoadState('load')
await page.waitForLoadState('domcontentloaded')
await page.waitForLoadState('networkidle')

await page.waitForResponse(urlPattern)
await page.waitForResponse(
  response => response.url().includes('/api/') && response.status() === 200
)

await page.waitForRequest(urlPattern)

// Custom timeout (extracted from user intent)
// "wait up to 10 seconds" → { timeout: 10000 }
await locator.waitFor({ state: 'visible', timeout: 10000 })

// Wait for element count
await expect(locator).toHaveCount(n, { timeout: 5000 })
```

### Network Interception

```typescript
// Observe API calls
page.on('request', request => { ... })
page.on('response', response => { ... })

// Wait for specific API call
await page.waitForResponse(r => r.url().includes('/api/login'))

// Mock a response
await page.route('**/api/endpoint', route =>
  route.fulfill({
    status: 200,
    body: JSON.stringify({ mock: 'data' })
  })
)

// Block requests
await page.route('**/*.png', route => route.abort())
```

### Tabs

```typescript
const pages = page.context().pages()
await pages[1].bringToFront()
await pages[0].close()
const tabCount = page.context().pages().length
```

### Screenshots

```typescript
await page.screenshot({ path: 'screenshot.png' })
await page.screenshot({ path: 'screenshot.png', fullPage: true })
await locator.screenshot({ path: 'element.png' })
await page.screenshot({ clip: { x, y, width, height } })
```

### JavaScript Evaluation

```typescript
await page.evaluate(() => { /* browser JS */ })
await page.evaluate(selector => document.querySelector(selector).value, sel)
await locator.evaluate(el => el.getAttribute('data-value'))
```

### Complete Assertions

```typescript
// Element state
await expect(locator).toBeVisible()
await expect(locator).toBeHidden()
await expect(locator).toBeEnabled()
await expect(locator).toBeDisabled()
await expect(locator).toBeChecked()
await expect(locator).toBeFocused()
await expect(locator).toBeEditable()
await expect(locator).toBeEmpty()

// Content
await expect(locator).toHaveText(text)              // exact match
await expect(locator).toContainText(text)           // partial match
await expect(locator).toHaveValue(value)
await expect(locator).toHaveAttribute(attr, value)
await expect(locator).toHaveClass(className)
await expect(locator).toHaveCSS(property, value)
await expect(locator).toHaveId(id)

// Count
await expect(locator).toHaveCount(n)

// Page level
await expect(page).toHaveURL(url)
await expect(page).toHaveURL(/pattern/)
await expect(page).toHaveTitle(title)

// All assertions support custom timeout
await expect(locator).toBeVisible({ timeout: 10000 })

// Soft assertions (continue after failure)
await expect.soft(locator).toBeVisible()
```

---

### How the agent loop works

This is the core brain of LLM Mode, but the LLM does **not** own the lifecycle. The Step Runner and Context Manager wrap the LLM tool-calling loop.

```python
async def run_llm_agent(steps: list, session_context: dict):

    # STEP 1: Step Runner initializes durable state
    step_runner.start(steps)
    # statuses: pending, planning, awaiting_confirmation, executing,
    #           recovery_pending, recorded, skipped

    # STEP 2: Context Manager builds full relevant state
    context = context_manager.build(
        steps=step_runner.state,
        page_state=browser_state,
        locator_library=locator_store.lookup(domain),
        page_map=page_map_store.lookup(url),
        history_summary=run_memory.summary(),
        skills=skill_router.select_depth(steps),
    )

    messages = context.to_messages()

    # STEP 3: Tool-calling loop
    while not step_runner.all_steps_done():
        response = await llm_client.chat.completions.create(
            model=config.model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:
            messages.append(message)

            for tool_call in message.tool_calls:
                # Runtime enforces lifecycle and tool preconditions.
                result = await runtime.execute_safely(tool_call, step_runner.state)

                # Tool result is appended, but large/raw results may later be
                # compacted into structured state by Context Manager.
                messages.append(tool_result(tool_call.id, result))

                step_runner.observe_tool_result(tool_call, result)

            messages = context_manager.compact_if_needed(messages, step_runner.state)
            continue

        # No tool calls does not automatically mean done.
        if step_runner.has_unresolved_work():
            correction = await ask_user_or_continue_recovery(message.content, step_runner.state)
            messages.append(user_recovery_message(correction))
            continue

        return message.content
```

### Why context is preserved without raw history bloat

The LLM receives full relevant state every call, but not necessarily full raw history.

Keep as structured state:

```text
current step statuses
confirmed plan
validated locators
current URL/title and DOM version
unresolved failed step
latest user correction
last successful action
page map summary
```

Compress or drop after summary:

```text
old raw DOM snippets
repeated screenshots
large actual page text
stale failed attempts
duplicate tool outputs
```

The model should never lose the reason for a decision, but it also should not carry every old byte of DOM forever.

### Tool registry

```python
TOOLS = [
    {
        "name": "locator_find",
        "description": "Find a locator for the element using a specific strategy",
        "parameters": {
            "element_data": "object",   # descriptor from overlay
            "strategy": "string"        # which strategy to attempt
        }
    },
    {
        "name": "locator_validate",
        "description": "Validate a locator string against the live page. Returns count.",
        "parameters": {
            "locator": "string"
        }
    },
    {
        "name": "action_execute",
        "description": "Execute a Playwright action on the live browser",
        "parameters": {
            "action": "string",         # click, fill, assert, navigate, etc.
            "locator": "string",
            "value": "string",          # optional
            "options": "object"         # timeout, modifiers, etc.
        }
    },
    {
        "name": "dom_snapshot",
        "description": "Get a DOM snapshot of an element or section",
        "parameters": {
            "scope": "string",          # "element" | "section" | "full_page"
            "element_data": "object"    # optional — if null, gets full page
        }
    },
    {
        "name": "page_map_read",
        "description": "Read stored page map for the current URL if it exists",
        "parameters": {
            "url": "string"
        }
    },
    {
        "name": "page_map_write",
        "description": "Save explored page structure to persistent storage",
        "parameters": {
            "url": "string",
            "map_data": "object"
        }
    },
    {
        "name": "send_to_panel",
        "description": "Send a message to the browser overlay panel",
        "parameters": {
            "type": "string",           # step_recorded, thinking, error, etc.
            "payload": "object"
        }
    },
    {
        "name": "memory_read",
        "description": "Read locator library or memory for this domain",
        "parameters": {
            "domain": "string",
            "key": "string"             # optional — if null, returns all
        }
    },
    {
        "name": "memory_write",
        "description": "Save a validated locator or pattern to persistent memory",
        "parameters": {
            "domain": "string",
            "key": "string",
            "value": "string"
        }
    },
    {
        "name": "screenshot",
        "description": "Take screenshot of page or element for visual analysis",
        "parameters": {
            "scope": "string",          # "page" | "element" | "region"
            "element_data": "object"    # optional
        }
    }
]
```

---

This is the most critical system. Everything must be validated against the live browser. When validation fails, the system recovers automatically before asking the human.

### Validation flow

```
Step is ready to execute
        ↓
Execute directly via ToolRuntime (no LLM)
        ↓
SUCCESS → record step → update memory → done ✅
        ↓
FAILURE → capture all failure data:
  - Exact error message
  - Error type (locator not found / not interactable /
                timeout / strict mode violation /
                frame detached / network failed)
  - Screenshot of current page state
  - What was attempted (action + locator + params)
        ↓
Decision tree — form ONE hypothesis:
```

### Recovery decision tree

```
ERROR: "Locator not found" (count = 0)
  HYPOTHESIS: locator changed or element not rendered yet
  FIX 1: re-run full locator waterfall on current page
  FIX 2: check if element is inside an iframe
  FIX 3: check if element is hidden/conditional
  FIX 4: waitForSelector then retry

ERROR: "Element not interactable"
  HYPOTHESIS: element exists but not ready for interaction
  FIX 1: scroll element into view → retry
  FIX 2: wait for animations to complete → retry
  FIX 3: check if covered by modal/overlay

ERROR: "Timeout exceeded"
  HYPOTHESIS: element taking longer than expected
  FIX 1: waitForLoadState('networkidle') → retry
  FIX 2: increase timeout → retry
  FIX 3: wait for specific element to appear instead of timeout

ERROR: "Strict mode violation" (count = 2+)
  HYPOTHESIS: locator not unique enough
  FIX 1: add parent context → retry
  FIX 2: add position constraint → retry
  FIX 3: add sibling relationship → retry

ERROR: "Frame detached"
  HYPOTHESIS: navigation happened during action
  FIX 1: waitForNavigation() → re-find element → retry

ERROR: "Network request failed"
  HYPOTHESIS: API call failed before page ready
  FIX 1: waitForLoadState('networkidle') → retry
```

### Recovery loop flow

```
Apply FIX 1
        ↓
Retry action
        ↓
PASS → continue silently. User never sees this happening. ✅
        ↓
FAIL → apply FIX 2 → retry
        ↓
FAIL → apply FIX 3 → retry
        ↓
All deterministic fixes exhausted
        ↓
LLM called with full failure context:
  "I tried:
   - Locator: [x] → 0 elements found
   - Waited for networkidle → still 0
   - Checked iframe context → not in iframe
   
   Current page screenshot: [attached]
   Current page URL: [url]
   
   What is wrong and how do I fix it?"
        ↓
LLM proposes solution
        ↓
System tries LLM solution
        ↓
PASS → continue ✅
        ↓
FAIL → LLM tries another approach
        ↓
LLM genuinely exhausted all strategies
        ↓
ASK HUMAN — ONE specific question:
  "Failing at: Step [N] — [action]
   Error: [specific error]
   I tried: [complete list]
   Current state: [screenshot]
   I need: [ONE specific question]"
        ↓
Human provides input
        ↓
LLM tries with new information
        ↓
Loop continues until:
  Fixed ✅ OR Human says stop ⏹

BROWSER NEVER CLOSES throughout this entire loop.
```

### Human controls during recovery

At any point during execution or recovery:

| Control | Keyboard | Behavior |
|---|---|---|
| **Pause** | Ctrl+P | Finish current action then pause. All state preserved. |
| **Stop** | Ctrl+. | Hard stop. Current action aborted. Browser stays open. All recorded steps preserved. |
| **Continue** | Ctrl+R | Resume from paused state. |
| **Skip** | Ctrl+K | Skip current failing step. Mark as skipped in output. Continue to next. |

---

Skills are plain text files. They are injected into the LLM system prompt before a run based on what the user is doing. They encode Playwright best practices, edge case handling, and patterns the LLM must follow.

### How skills are loaded

Skills use **progressive disclosure**. Do not load every full `SKILL.md` file just because a keyword appears.

#### Skill loading levels

| Level | What is loaded | When |
|---|---|---|
| Level 0 | Skill index: name, description, triggers, available tools | Always |
| Level 1 | Compact skill summary: critical rules and tool names | Intent likely needs the skill |
| Level 2 | Full `SKILL.md` body | The current step requires details or risk is high |
| Level 3 | Deep reference/examples | Debug/recovery or rare edge case |

#### Skill router behavior

```python
def build_prompt_context(steps, run_state):
    skill_index = read_skill_index()  # always cheap

    selected = skill_router.classify(
        intents=[s.intent for s in steps],
        failures=run_state.failures,
        current_page=run_state.page_state,
    )

    prompt_parts = [read_compact_core_rules(), skill_index]

    for skill in selected:
        if skill.confidence == "low":
            prompt_parts.append(read_skill_summary(skill.name))
        elif skill.risk == "high" or run_state.is_recovery:
            prompt_parts.append(read_full_skill(skill.name))
        else:
            prompt_parts.append(read_skill_summary(skill.name))

    return "\n\n".join(prompt_parts)
```

#### Important rules

```text
Core rules are always present, but compact.
Skill descriptions are always available through the skill index.
Full skill files are loaded only when needed.
Large examples/reference docs are loaded only in debug/recovery mode.
Skill loading must be logged with token estimates.
```

This prevents prompt bloat while preserving quality when complex actions such as upload, iframe, popup, or custom dropdown handling are needed.

### Skills list

```
.hermes/skills/playwright-automation/
  ├── core/SKILL.md           ← always loaded — persona, rules, locator priority
  ├── locator/SKILL.md        ← find, locate, element, selector
  ├── actions/SKILL.md        ← click, fill, hover, press, drag
  ├── assertions/SKILL.md     ← assert, verify, expect
  ├── waiting/SKILL.md        ← wait, loading, timeout, spinner
  ├── popup/SKILL.md          ← popup, dialog, alert, confirm
  ├── upload/SKILL.md         ← upload, file, attach, chooser
  ├── download/SKILL.md       ← download, save, export
  ├── tab/SKILL.md            ← new tab, window, opens tab
  ├── iframe/SKILL.md         ← iframe, frame, nested
  ├── shadow_dom/SKILL.md     ← shadow DOM, web components
  ├── dropdown/SKILL.md       ← select, dropdown, autocomplete
  ├── dynamic/SKILL.md        ← SPA, React, Angular, loading
  ├── keyboard/SKILL.md       ← press, key, shortcut
  ├── scroll/SKILL.md         ← scroll, infinite scroll
  ├── auth/SKILL.md           ← login, auth, storage state
  ├── network/SKILL.md        ← API, intercept, mock, observe
  ├── mobile/SKILL.md         ← mobile, viewport, touch
  ├── console/SKILL.md        ← console errors, JS errors
  ├── trace/SKILL.md          ← trace recording, replay
  ├── exploration/SKILL.md    ← page analysis, page mapping
  ├── codegen/SKILL.md        ← TypeScript generation rules
  ├── debugging/SKILL.md      ← failure recovery, error diagnosis
  └── screenshot/SKILL.md     ← screenshots, visual capture
```

### Core skill content (always loaded)

The core skill encodes the fundamental rules:
- The LLM persona (senior Playwright engineer)
- The 10 hard rules
- Locator priority order
- Never use sleep()
- Token efficiency rules
- TypeScript as output language
- How to ask clarifying questions
- How to handle uncertainty

**core/SKILL.md is human-editable only. No agent can modify it.**

---

These cannot be overridden. Ever. They live in `core/SKILL.md` and are enforced in every code path.

1. **Browser NEVER closes during session.** Only when user explicitly ends it.
2. **Every locator must match exactly 1 element.** Never proceed with 0 or 2+ matches.
3. **Reduce human effort — never increase it.** Every decision is made to save user time.
4. **Never use sleep() or arbitrary timeouts.** Condition-based waits only.
5. **Never crash on failure — always recover.** Recovery loop runs. Browser stays open.
6. **Never make the same mistake twice.** Update memory after every failure + fix.
7. **Never touch auth unless user explicitly asks.** Auth is 100% user-controlled.
8. **Never log or display secret values.** `.env` values never appear in chat or logs.
9. **Programmatic first, LLM second.** LLM is called only when code cannot solve it.
10. **Output is immediately usable.** Generated TypeScript runs with `npx playwright test`. No cleanup needed.

---

This addendum tightens the PRD based on implementation learnings from the LLM Mode prototype and current browser-agent best practices. It does **not** replace the existing architecture. It clarifies ownership boundaries so the system remains reliable as more actions, recovery flows, and generated code features are added.

### 25.1 Design principle

The LLM should reason, plan, and explain. It must not own product state.

**Runtime ownership:**

| Layer | Owns | Must not delegate to LLM |
|---|---|---|
| Step Runner | Step lifecycle, confirmation gates, execution order, final completion | Whether a step is done |
| Context Manager | What the LLM sees per call | Raw full history by default |
| Tool Runtime | Browser actions, locator validation, tool preconditions | Unsafe tool calls |
| Recorder / Codegen | Recorded step payloads and TypeScript output | Backend truth from free-form text |
| LLM | Intent interpretation, planning, recovery reasoning | State transitions, recording truth, final completion |

Hard rule:

```text
The LLM may suggest. The runtime decides.
```

### 25.2 Context Manager

The system must include a first-class Context Manager. It owns prompt construction for every LLM call.

Responsibilities:

- Select relevant skills only.
- Include compact step state.
- Include current browser state: URL, title, page identity, DOM version.
- Include focused DOM snippets only when needed.
- Include validated locators from the locator library.
- Include page map summaries instead of full DOM on revisits.
- Include unresolved failure context.
- Compress or drop stale tool outputs.
- Track approximate input/output tokens and cost per LLM call.

The LLM must receive **full relevant state**, not raw full history.

#### Managed history policy

Keep:

```text
current step queue and statuses
confirmed plan
user corrections
validated locator choices
current page URL/title
unresolved failure details
latest focused DOM snapshot
```

Compress or drop:

```text
repeated full DOM snapshots
repeated long page text
stale failed locator attempts after summary
screenshot metadata after failure summary
old tool results that no longer affect current state
```

#### Token telemetry requirement

Every LLM request must log:

```text
model
loaded skills
system prompt tokens
messages/history tokens
tool schema tokens
DOM/tool-result tokens
total input tokens
output tokens
estimated cost
```

This is required before optimizing DOM/page-map behavior. Without telemetry, token strategy is guesswork.

### 25.3 Step Runner owns lifecycle

The Step Runner owns the lifecycle for every step. It is the source of truth for whether work is pending, confirmed, failed, recorded, skipped, or complete.

Required step statuses:

```text
pending
planning
validated
awaiting_confirmation
confirmed
executing
failed
recovery_pending
recorded
skipped
```

Allowed state flow:

```text
pending → planning → validated → awaiting_confirmation → confirmed → executing → recorded
```

Failure flow:

```text
executing → failed → recovery_pending → recovered execution → recorded
```

Skip flow:

```text
failed/recovery_pending → user explicitly says skip → skipped
```

Hard rules:

```text
Execution tools cannot run before confirmation.
step_recorded cannot happen before confirmed successful execution.
The LLM cannot finalize while any step is pending, failed, executing, or recovery_pending.
Final response is allowed only when all requested steps are recorded or explicitly skipped.
```

The system must never treat phrases such as “completed,” “done,” or “successfully” as final truth if the Step Runner state says unresolved work remains.

### 25.4 Backend-owned recording

Recording is backend-owned, not LLM-owned.

Correct recording flow:

```text
confirmed action/assertion succeeds
→ Step Runner verifies success
→ Recorder builds step_recorded payload
→ backend sends step_recorded event
→ UI renders recorded step
→ codegen updates generated code
```

The LLM may provide suggested metadata, but the backend must repair or generate missing fields.

Required `step_recorded` payload:

```json
{
  "type": "step_recorded",
  "step_id": "client-step-id",
  "step_number": 1,
  "status": "recorded",
  "action": "click | fill | assert | navigate | ...",
  "element_name": "human readable target",
  "locator": "validated locator string",
  "generated_line": "await page...",
  "source_intent": "original user intent"
}
```

If the LLM omits `step_id`, action, or locator, the backend must recover them from step state and last successful action. If the backend cannot map a successful action to a step, it must not silently record; it must surface a structured error.

### 25.5 Typed WebSocket protocol

All backend ↔ overlay messages must have typed schemas. Missing required fields must fail visibly.

Core event types:

```text
llm_thinking
plan_ready
clarification_needed
correction_received
execution_started
execution_progress
step_recorded
step_failed
recovery_required
code_update
error
```

`plan_ready` must include:

```json
{
  "type": "plan_ready",
  "summary": "human readable summary",
  "steps": [
    {
      "step_id": "...",
      "intent": "...",
      "planned_action": "...",
      "target": "...",
      "locator_preview": "optional"
    }
  ],
  "requires_confirmation": true
}
```

`code_update` must include:

```json
{
  "type": "code_update",
  "step_id": "...",
  "generated_line": "await page...",
  "full_code_preview": "optional"
}
```

UI buttons must have unambiguous behavior:

```text
Confirm = accept plan and execute.
Send Correction = reject/revise plan using typed correction text.
```

### 25.6 DOM freshness and invalidation rules

Every DOM extraction and validated locator belongs to a page state.

Track:

```text
page_url
page_title
dom_version
extraction_scope
created_at
invalidated_by
```

Any browser-mutating action increments or invalidates DOM state:

```text
click that may navigate
page_navigate
page_go_back
page_go_forward
page_reload
form submit
popup/new tab open
DOM-changing interaction
```

Rules:

```text
After navigation/reload/back/forward, old DOM snapshots are stale.
After a click that changes page state, later assertions must revalidate against current DOM.
Do not execute a same-page assertion from an old snapshot after a navigation action.
If a tool batch contains a mutating action followed by another browser action/assertion, execute the mutating action first, then re-query LLM with updated browser state.
```

### 25.7 Tool safety policy

All tools must declare preconditions and enforce them before calling Playwright.

Examples:

```text
action_fill: allowed only on input, textarea, select, or contenteditable; reject body/div/span/etc.
page_go_back: use for browser history back; never simulate navigation with fill/click on body.
action_assert: must revalidate locator if DOM version changed.
file upload: must verify file exists under approved upload directory.
download: must register download listener before click.
popup/dialog: must register handler before triggering action.
```

Tool failures must produce structured results:

```json
{
  "success": false,
  "error": "...",
  "tool": "action_fill",
  "recoverable": true,
  "requires_user_input": false,
  "step_id": "..."
}
```

### 25.8 Recovery anchoring

Recovery must stay anchored to the original failed step.

When a failure occurs, the LLM must receive:

```text
failed step id
step number
original user intent
selected element info
validated locator if any
current browser URL/title
last successful action
last error
available recovery options
```

Hard rule:

```text
The agent must recover the original failed step. It must not replace it with a new unrelated assertion/action unless the user explicitly asks.
```

Example failure:

```text
Original intent: assert homepage heading after clicking Get Started.
Current URL: /docs/intro.
Failure: homepage heading not found.
```

Correct recovery options:

```text
go back and assert before click
navigate to homepage and assert
ask user whether to skip or revise
```

Incorrect recovery:

```text
assert an unrelated heading on /docs/intro just because it exists
```

### 25.9 Model routing strategy

MVP may use one model, but the architecture must allow future model routing.

Recommended roles:

| Role | Purpose | Model size |
|---|---|---|
| Main reasoning model | planning, recovery, tool choice | strongest available |
| Page extraction model | summarize DOM/page content | smaller/faster |
| Judge model | optional trace quality validation | medium/strong |
| Fallback model | provider/model failure recovery | alternate provider/model |

Do not implement multi-model routing before the basic LLM Mode is stable. Design interfaces so it can be added later without rewriting the agent loop.

### 25.10 Overlay architecture decision

The MVP overlay is a direct injected in-page overlay, not an iframe.

Decision:

```text
MVP: direct injected overlay
Stabilized version: Shadow DOM overlay
Future product option: Chrome extension or separate control panel
Avoid iframe unless CSP and cross-origin constraints are solved
```

Rationale:

```text
Direct overlay: best for current element picking and fast iteration; weaker CSS isolation.
Shadow DOM overlay: better CSS/layout isolation and still supports page interaction; recommended next stabilization step.
Iframe overlay: stronger UI isolation but cross-origin/CSP and picker complexity; not preferred for MVP.
```

### 25.11 Edge cases that must be covered by tests

Plan / correction:

```text
user confirms correct plan
user sends correction before execution
user types correction but clicks wrong button
user says stop/skip during recovery
```

DOM / locator:

```text
selected section is too large
same text appears multiple times
text has &nbsp;, child spans, hidden/control characters
locator valid before navigation but invalid after navigation
element is inside iframe/shadow DOM
```

Execution:

```text
click navigates before old-page assertion
click opens popup/new tab
dialog must be handled before click
download listener must be registered before click
upload needs missing file handling
fill is attempted on non-editable element
```

Recovery:

```text
tool fails after partial success
recovery needs page_go_back
recovery must not drift to unrelated assertion
failed step must remain unresolved until recorded/skipped
```

Recording / codegen:

```text
step_recorded missing metadata
multi-action single intent needs deterministic sub-step handling
generated code must use valid Playwright TypeScript syntax
replay must revalidate locator before execution
```

Session:

```text
browser reconnects while steps exist
recorded steps must not rerun unless user asks
confirmed steps must be autosaved later
```

### 25.12 Updated LLM Mode implementation order

After the current agent loop is functional, prioritize:

```text
1. Recorded Steps UI stabilization
2. Live code_update event and code preview
3. Locator-string-to-TypeScript conversion
4. Token telemetry for every LLM call
5. Replay single recorded step
6. Replay all recorded steps
7. Context Manager / managed history
8. Progressive skill loading
9. DOM modes: normal / explore / debug / full fallback
10. Persistent locator library
11. Page maps and revisit compression
12. Advanced action vocabulary: hover, press, select, upload, download, popup, iframe, network
13. Session persistence and final .spec.ts output
```

Do not expand advanced vocabulary before recorded steps, code preview, and replay are usable enough to test reliably.
---

This section clarifies how LLM Mode should balance reliability and cost. The goal is not to minimize tokens blindly. The goal is to preserve decision quality while removing irrelevant context.

### 26.1 Core rule

```text
Give the LLM full relevant state, not raw full history.
```

The LLM must always know:

```text
what the user asked
which step is active
which plan was confirmed
which locators are validated
which page state is current
what failed and why
what correction the user gave
what still remains unresolved
```

The LLM does not need every old raw DOM dump, repeated screenshot path, or duplicate failed attempt once those details have been summarized into structured state.

### 26.2 Context Manager responsibilities

`ContextManager` is a first-class component. It owns the prompt/context package for each LLM call.

Responsibilities:

```text
select skill depth
choose DOM mode
include step state
include current browser state
include validated locators
include page map summary
include active failure context
compact old history
enforce token budget
log token telemetry
escalate context when quality requires it
```

The agent loop should ask the Context Manager for context. It should not manually concatenate every available file and every old tool output.

### 26.3 Progressive skill loading

Skill loading must be progressive.

```text
Always loaded: compact core rules + skill index
Usually loaded: compact summaries for likely skills
Only when needed: full SKILL.md
Rare/debug only: deep examples and reference files
```

Example:

```text
User intent: "click Get started"
Context: core compact rules + actions summary + locator summary
Do not load: upload, download, iframe, network, auth, visual, mobile

User intent: "upload resume and verify success modal"
Context: core compact rules + actions summary + upload full skill + assertions summary + popup/modal summary

Failure: file chooser did not appear
Context escalates: upload details + screenshot/debug context + tried actions
```

### 26.4 DOM mode decision tree

```text
Selected single element?
  → Normal mode descriptor.

Selected section?
  → Accessibility tree if useful.
  → Else cleaned interactive subtree.
  → If too large, ask user to narrow.

No element or page-level instruction?
  → Explore mode page map.

Tool failed once?
  → Debug mode around failed target.

Repeated failure or unknown structure?
  → Explore changed area or focused full-page map.

Still ambiguous?
  → Ask one user question.

Only as last resort or explicit user request?
  → Full DOM fallback with cap and reason logged.
```

### 26.5 History compaction policy

After each meaningful phase, raw tool history may be compacted into a structured summary.

Keep exactly:

```text
current queued steps
step statuses
confirmed plan
current page URL/title/dom_version
validated locators
active failure context
user correction text
last successful action
recorded step metadata
```

Compress:

```text
old raw DOM snippets → section summary
long actual text → truncated normalized text + reason
repeated locator attempts → tried strategies summary
screenshot metadata → latest screenshot only
old tool outputs → phase summary
```

Never compress away unresolved work.

### 26.6 Token budgets

Budgets are guardrails, not hard correctness limits. If quality requires escalation, escalate and log why.

| Call type | Target input tokens | Allowed escalation |
|---|---:|---|
| Normal selected-element call | 4k–8k | Add nearby DOM if locator confidence is low |
| Section interaction | 6k–12k | Add interactive subtree or accessibility tree |
| Explore mode | 8k–15k | Split by sections rather than one huge call |
| Debug/recovery | 10k–20k | Include focused DOM, failure, screenshot path, tried locators |
| Full DOM fallback | Explicit/capped | Last resort only; must log reason |

### 26.7 Token telemetry

Every LLM call must log:

```text
model
call purpose: normal / explore / debug / recovery / codegen
loaded skill levels
system prompt tokens
skill tokens
tool schema tokens
message/history tokens
DOM/tool-result tokens
total input tokens
output tokens
estimated cost
context mode used
compaction applied: yes/no
```

Without telemetry, optimization is guesswork.

### 26.8 Quality-preservation rules

Context reduction must never remove:

```text
active failed step
current user correction
confirmed plan
current page URL/title
validated locator for active step
reason previous attempt failed
step state and remaining work
```

If removing context would make the next decision unsafe, keep the context or ask the user.

### 26.9 Repeated failure escalation

```text
First failure:
  Use focused debug context around the target.

Second similar failure:
  Include tried strategies, current URL, current DOM section, and page map.

Third similar failure:
  Ask user one specific question or offer concrete options.

After user correction:
  Preserve correction exactly and anchor recovery to original failed step.
```

The agent must not loop silently. It must either recover deterministically, escalate context, or ask the user.

### 26.10 Implementation order for context hardening

Do not build the entire Context Manager before the product loop is usable. Implement in stages:

```text
1. Token telemetry for every LLM call
2. Skill index + compact skill summaries
3. History compaction after tool phases
4. DOM modes: normal / explore / debug / full fallback
5. Page map reuse
6. Persistent locator library reuse
7. Optional model routing for extraction/judge/fallback
```

This keeps progress practical while preventing future token explosions.