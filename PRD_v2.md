# Playwright Automation Co-pilot — PRD v2

> **Status:** Active  
> **Version:** 2.0  
> **Replaces:** document_prd.md (v1 — archived)  
> **Decision:** Build fresh using existing `execution/`, `locator/`, `storage/` as reference components

---

## Table of Contents

1. [Why We Are Building This](#1-why-we-are-building-this)
2. [What Went Wrong in v1](#2-what-went-wrong-in-v1)
3. [What We Are Building](#3-what-we-are-building)
4. [Architecture](#4-architecture)
5. [The Two Modes](#5-the-two-modes)
6. [DOM Strategy & Token Optimization](#6-dom-strategy--token-optimization)
7. [Locator Engine](#7-locator-engine)
8. [Complete Playwright Vocabulary](#8-complete-playwright-vocabulary)
9. [The LLM Layer](#9-the-llm-layer)
10. [The Validation & Recovery Loop](#10-the-validation--recovery-loop)
11. [The Skills System](#11-the-skills-system)
12. [Memory & Persistence](#12-memory--persistence)
13. [The Overlay UI](#13-the-overlay-ui)
14. [WebSocket Protocol](#14-websocket-protocol)
15. [Session Management](#15-session-management)
16. [Data Input Methods](#16-data-input-methods)
17. [Authentication & Storage State](#17-authentication--storage-state)
18. [Output — Generated Code](#18-output--generated-code)
19. [Features Scope — v1](#19-features-scope--v1)
20. [The 10 Hard Rules](#20-the-10-hard-rules)
21. [What to Keep from Existing Codebase](#21-what-to-keep-from-existing-codebase)
22. [What to Rebuild](#22-what-to-rebuild)
23. [Folder Structure](#23-folder-structure)
24. [Build Order](#24-build-order)

---

## 1. Why We Are Building This

Automation testers waste enormous time on things that should be automatic:

| Problem | Impact |
|---|---|
| **Intent Communication** | No reliable way to express intent clearly. Natural language is ambiguous. No structured way to point at what you mean on the page. |
| **Intent vs Reality Mismatch** | System interprets what user said but does not ground it against what actually exists in the DOM. Acts on assumptions, not reality. |
| **Locator Quality** | Finding *a* locator is easy. Finding the *right* one — stable, unique, resilient to page changes — is the actual hard problem. |
| **Locator Validation Gap** | No way to know if a locator works until execution fails. No real-time feedback between "found" and "confirmed working." |
| **No Interactive Recovery** | When something breaks, the only option is restart. No way to fix, correct, or continue in place. |
| **Uncontrolled Execution** | System wanders, makes assumptions, loses track of the original goal without checkpoints. |
| **Unusable Output** | Final generated code needs cleanup before it is actually useful. Not directly runnable. |

**The goal:** Reduce human effort to the minimum. Human tells the system what to test. System figures out how, validates it, fixes failures, and produces clean runnable Playwright TypeScript. Human stays in control but does none of the mechanical work.

---

## 2. What Went Wrong in v1

### The Hermes mistake

v1 integrated the Hermes agent framework as the brain. Hermes is **synchronous**. Playwright is **async**. This caused an endless cascade of problems:

- Hermes was wired with `enabled_toolsets=[]` — no tools, no skills, no memory
- `max_iterations=1` — single turn only, no multi-step reasoning
- The entire brain had to be reimplemented manually in `agent_ws_loop.py` (1059 lines)
- Everything that Hermes was supposed to do was duplicated in Python outside Hermes
- Skills existed but were never loaded
- Memory existed but was never connected

### The lesson

**Never mix a synchronous agent framework into an async Playwright system.** The architecture must be async-native from the ground up — no bridges, no wrappers, no sync calls inside async paths.

### What the existing codebase got right

The existing project (pre-Hermes) has solid foundations:
- `execution/browser.py` — async Playwright browser lifecycle ✅
- `execution/tools.py` — complete Playwright action vocabulary ✅
- `execution/runner.py` — step execution with retries and events ✅
- `locator/engine.py` — multi-strategy locator ranking with confidence ✅
- `healing/force_fix.py` — 4-stage deterministic + LLM repair cascade ✅
- `healing/llm_assist.py` — multi-attempt LLM repair loop ✅
- `llm/provider.py` — OpenAI, Anthropic, OpenAI-compatible abstraction ✅
- `storage/` — SQLite repos, migrations, versioning ✅

The `LLMOrchestrator` in `llm/orchestrator.py` also exists and is exactly what we need — a multi-turn tool-calling loop. It just was never connected to the panel. That is the architectural fix.

---

## 3. What We Are Building

**An AI-powered browser automation co-pilot for Playwright automation testers.**

The user opens a browser, points at things on the page, describes what they want, and the system produces clean, validated, directly runnable Playwright TypeScript test scripts.

Two modes. One output. Zero mechanical work for the human.

### Core principles

- **Human effort is minimized, not eliminated.** Human tells what. System figures out how.
- **Everything is live.** Browser is always open. Every locator is validated against the real DOM right now.
- **LLM is intelligence, not a crutch.** Programmatic solutions first. LLM only when code cannot solve it.
- **Never crash. Always recover.** Failures trigger the recovery loop. Browser never closes.
- **Output is immediately usable.** Generated TypeScript runs with `npx playwright test`. No cleanup needed.

---

## 4. Architecture

### System diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Playwright Chromium Browser (headed, persistent)            │
│                                                              │
│  ┌──────────────────────────────┐  ┌──────────────────────┐ │
│  │   LIVE WEBSITE               │  │  CO-PILOT PANEL      │ │
│  │   (user browses normally)    │  │  [Manual | LLM]      │ │
│  │                              │  │  Step list           │ │
│  │   [highlighted element]      │  │  Code view           │ │
│  │   shown on hover/select      │  │  Chat input          │ │
│  │                              │  │  Controls            │ │
│  └──────────────────────────────┘  └──────────────────────┘ │
└──────────────────────────────┬──────────────────────────────┘
                               │ CDP injection
                               │ iframe panel served locally
                               │ WebSocket ws://localhost:PORT
┌──────────────────────────────▼──────────────────────────────┐
│  Python asyncio Backend                                      │
│                                                              │
│  PanelBridge (WebSocket server — thin router)                │
│       │                                                      │
│       ├── Manual Handler                                     │
│       │     locator waterfall (no LLM)                       │
│       │     direct tool execution                            │
│       │     LLM only on validation failure                   │
│       │                                                      │
│       └── LLM Agent Loop                                     │
│             build messages[] with full context               │
│             load relevant skills into system prompt          │
│             call LLM via provider (any model)                │
│             execute tool calls (async Playwright)            │
│             append results to messages[]                     │
│             loop until all steps complete                    │
│                                                              │
│  Tool Registry (async Python functions)                      │
│    locator_find | locator_validate | action_execute          │
│    send_to_panel | memory_read | memory_write                │
│    dom_snapshot | page_map_read | page_map_write             │
│                                                              │
│  Execution Layer (from existing codebase — keep as-is)       │
│    BrowserSession | ToolRuntime | StepGraphRunner            │
│    LocatorEngine | HealingFlows | LLMProviders               │
│                                                              │
│  Persistence                                                 │
│    SQLite (steps, sessions, events, checkpoints)             │
│    JSON files (locator library, page maps, memory)           │
│    .env (secrets — never logged)                             │
└──────────────────────────────┬──────────────────────────────┘
                               │ OpenAI-compatible API
┌──────────────────────────────▼──────────────────────────────┐
│  LLM Provider (any — swap base_url)                          │
│  OpenAI | Anthropic | Ollama | LM Studio | any               │
└─────────────────────────────────────────────────────────────┘
```

### Key architectural decisions

**1. Fully async — no exceptions**  
Every component uses `asyncio`. No sync calls inside async paths. No bridges. No wrappers. This is the single most important lesson from v1.

**2. OpenAI-compatible LLM client**  
One client, any provider:
```python
client = openai.AsyncOpenAI(
    base_url="https://api.openai.com/v1",  # swap for any provider
    api_key=os.getenv("LLM_API_KEY")
)
# Anthropic: base_url="https://api.anthropic.com/v1"
# Ollama:    base_url="http://localhost:11434/v1"
# LM Studio: base_url="http://localhost:1234/v1"
```

**3. messages[] list IS the memory**  
Every LLM call sends the complete conversation history. The LLM is stateless — the Python list is the state. This solves the "LLM doesn't remember what it tried" problem completely.

**4. PanelBridge is a thin router**  
It receives WebSocket messages and routes to the correct handler. It contains zero business logic. All intelligence lives in the LLM agent loop or the manual handler.

**5. iframe injection, not Shadow DOM**  
Panel is served as a local HTTP page and injected as an iframe via `add_init_script`. CDP session ensures injection survives CSP. Panel reinjects on every page `load` event for navigation resilience.

---

## 5. The Two Modes

### Mode 1 — Manual Mode

**Who uses it:** User who wants precise, predictable control over every action.

**How it works:**
```
User activates Pick tool
        ↓
User clicks element on page
        ↓
System captures element descriptor
  (tag, id, role, aria-label, text, parent, siblings)
        ↓
System runs locator waterfall immediately (programmatic, no LLM)
        ↓
Panel shows: best locator found + confidence score
User sees element highlighted on page
        ↓
User selects action from dropdown
  (all Playwright actions available — see Section 8)
User enters value if needed
        ↓
System validates immediately:
  Executes action against live browser
  Checks result
        ↓
PASS → step appended to session
FAIL → LLM kicks in for THIS problem only:
  Sends: element snapshot + error + what was tried
  LLM suggests fix
  System tries fix
  Still failing → recovery loop (see Section 10)
        ↓
Step confirmed → code view updates live
```

**Key distinction:** In Manual mode, the LLM is only called when something fails. The human explicitly chose every action. The LLM is the repair mechanic, not the driver.

**Special case handling in Manual mode:**  
The system detects special cases from the action chosen and element context, and handles them automatically:

| User action | System detects | System does automatically |
|---|---|---|
| Click on element that triggers popup | popup/dialog skill | Registers `page.on('dialog')` handler BEFORE click |
| Click on link that opens new tab | new tab skill | Sets up `context.waitForPage()` BEFORE click |
| Upload action | upload skill | Selects correct upload strategy (input/chooser/drag) |
| Click inside iframe | iframe skill | Enters frame context first |
| Select from dynamic dropdown | dropdown skill | Click trigger → wait for options → click option |

User does not need to know any of this. They just pick the action. The system handles the complexity.

---

### Mode 2 — LLM Mode

**Who uses it:** User who wants to describe intent in plain English and let the system figure out everything.

**How the user builds steps — the multi-element flow:**

In LLM mode, the user builds a step list BEFORE hitting run. Each step can optionally have an element picked for context. This is the key workflow:

```
BUILDING PHASE (before hitting Run):

User adds Step 1:
  (Optional) Click [🔍 Pick] → click element on page
  Panel shows picked element as context
  User types intent in the step input:
    "click this login button"
  [+ Add Step] — step added to queue, NOT executed yet

User adds Step 2:
  (Optional) Click [🔍 Pick] → click different element
  User types intent:
    "fill this email field with test@example.com"
  [+ Add Step]

User adds Step 3:
  No element picked (not always needed)
  User types intent:
    "assert the dashboard heading is visible"
  [+ Add Step]

User adds Step 4:
  User types multi-action intent (no element needed):
    "go to the results page, explore all sections,
     and add assertions for every visible heading
     and every data count badge"
  [+ Add Step]

Step queue now shows:
  1. [🔵 Login button] "click this login button"
  2. [🔵 Email field]  "fill email with test@example.com"
  3. [no element]      "assert dashboard heading is visible"
  4. [no element]      "explore results page, add assertions..."

User reviews the queue. Can:
  - Edit any step's intent text
  - Re-pick the element for any step
  - Delete any step
  - Reorder steps

User clicks [▶ Run All]
        ↓
LLM Agent Loop starts — processes ALL steps in sequence
```

**The step input UI in LLM mode:**

```
┌──────────────────────────────────────────────────┐
│ LLM MODE — Build your steps                      │
├──────────────────────────────────────────────────┤
│ [🔍 Pick element] (optional — gives LLM context) │
│ Selected: Login button (button#login-btn)         │
│                                                  │
│ What should happen with this?                    │
│ [click this login button               ]         │
│                                                  │
│ [+ Add Step]                                     │
├──────────────────────────────────────────────────┤
│ STEP QUEUE:                                      │
│ 1. 🔵 Login btn  "click this login button"  [✏️🗑] │
│ 2. 🔵 Email fld  "fill email with test@..."  [✏️🗑] │
│ 3.    —          "assert dashboard visible" [✏️🗑] │
│ 4.    —          "explore results page..."  [✏️🗑] │
│                                                  │
│ [▶ Run All]  [Clear Queue]                       │
└──────────────────────────────────────────────────┘
```

**Element context is optional — the LLM decides when it needs it:**
- Simple action + picked element → LLM uses element data directly for locator
- Complex intent + no element → LLM explores the page to find what it needs
- Page-level intent (explore, assert all, etc.) → element not needed at all

**How it works after [Run All]:**
```
LLM Agent Loop starts:

  STEP 1: Build system prompt
    Load core skill (always)
    Detect keywords across ALL steps → load relevant skills
    Load locator library for this domain
    Load page map if exists
    Load session memory
        ↓
  STEP 2: Build messages[]
    [system]: full context (skills + memory + locators)
    [user]: all steps with their element data + intent text
        ↓
  STEP 3: The loop
    LLM processes steps one by one
    For each step:
      finds locator (uses element data if provided)
      handles special cases (popups, iframes, tabs)
      executes action
      validates result
      appends to messages[]
    If step fails → recovery loop
    If genuinely stuck → asks user ONE question
    Continues until all steps complete
        ↓
  STEP 4: Output
    All steps validated
    TypeScript generated
    Locator library updated
    Memory updated
    Panel shows results
```

**The LLM persona:**  
The LLM does not behave as a generic assistant. It has a specific persona baked into the system prompt:

```
You are a senior Playwright automation engineer with deep expertise in:
- Finding stable, resilient locators for any element on any page
- Handling every Playwright edge case: iframes, popups, new tabs,
  dynamic dropdowns, file uploads, SPAs, shadow DOM
- Writing clean, maintainable TypeScript test scripts
- Understanding what QA engineers actually need to test
- Interpreting natural language test descriptions precisely

When you receive a test intent:
1. Think like a QA engineer: what is the user actually trying to verify?
2. Use the element data and DOM context to find the best locator
3. Handle all edge cases proactively (popups, waits, frames)
4. If the intent is unclear, ask ONE specific clarifying question
5. Never assume and proceed wrong
6. Suggest assertions the user may have missed
7. Always produce clean, directly runnable TypeScript

You have access to tools. Use them. Do not just describe what to do — do it.
```

**LLM Mode exploration example:**
```
User step: "Go to this results page and explore all sections.
            Understand the layout. Then suggest assertions."

LLM actions:
  1. Calls dom_snapshot(scope="full_page")
  2. Calls page_map_read(url=current_url) — check if already explored
  3. If not cached: systematically reads each section
  4. Sends back to panel:
     "I found 4 sections:
      1. Header — title, export button, breadcrumb
      2. Filter bar — 6 filter inputs, reset button
      3. Results table — 8 columns, pagination
      4. Footer — count badge, total value
      
      Suggested assertions:
      - Header title is visible and not empty
      - Filter bar has exactly 6 inputs
      - Table has at least 1 row
      - Count badge contains a number (not zero)
      - Export button is enabled
      
      Want me to add these?"
        
User: "Yes, add those. Also assert the URL contains /results"

LLM: generates all assertions with validated locators
     adds to step list
     shows code preview
```

---

## 6. DOM Strategy & Token Optimization

### The core principle

**Measure first. Decide after. Never send more than needed.**

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

## 7. Locator Engine

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

## 8. Complete Playwright Vocabulary

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

## 9. The LLM Layer

### How the agent loop works

This is the core brain of LLM mode. It is a standard OpenAI tool-calling loop — async, stateful within a run via the messages[] list.

```python
async def run_llm_agent(steps: list, session_context: dict):

    # STEP 1: Build system prompt with skills
    system = build_system_prompt(steps, session_context)
    # Includes: persona + core rules + relevant skills +
    #           locator library + page map + memory

    # STEP 2: Initialize messages list
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": format_steps(steps)}
    ]

    # STEP 3: Tool-calling loop
    while True:
        response = await llm_client.chat.completions.create(
            model=config.model,
            messages=messages,           # FULL history every call
            tools=TOOL_DEFINITIONS,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:
            # LLM wants to call a tool
            messages.append({"role": "assistant", "content": message})

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                # Execute against live browser (async)
                result = await execute_tool(name, args)

                # Append result — LLM sees this on next call
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
            # Loop — LLM now has full history of what happened
            continue

        else:
            # LLM is done — no more tool calls
            return message.content
```

### Why context is never lost

Every single tool call and its result gets appended to messages[]. On the next LLM call, the model sees the complete history:

```
system: [persona + skills + memory + locator library]
user: "find locator for login button, element: {data-testid: null, id: null...}"
assistant: → called locator_find(strategy="data-testid") 
tool: "result: 0 elements found"
assistant: → called locator_find(strategy="aria-label")
tool: "result: 0 elements found"
assistant: → called locator_find(strategy="text_content", text="Login")
tool: "result: 1 element found — locator: text=Login"
assistant: → called locator_validate(locator="text=Login")
tool: "valid: true, count: 1, stable: medium"
assistant: → called action_execute(action="click", locator="text=Login")
tool: "success: true, duration: 120ms"
assistant: → called send_to_panel(type="step_recorded", ...)
tool: "sent: true"
```

The LLM never "forgets" because every attempt and result is in the messages list that it receives on every call.

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

## 10. The Validation & Recovery Loop

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

## 11. The Skills System

Skills are plain text files. They are injected into the LLM system prompt before a run based on what the user is doing. They encode Playwright best practices, edge case handling, and patterns the LLM must follow.

### How skills are loaded

```python
SKILL_TRIGGERS = {
    "core":       None,                          # always loaded
    "locator":    ["find", "locate", "element", "selector", "pick"],
    "actions":    ["click", "fill", "type", "hover", "press", "double", "right"],
    "assertions": ["assert", "verify", "check", "expect", "should", "validate"],
    "waiting":    ["wait", "loading", "spinner", "slow", "timeout", "appear", "disappear"],
    "popup":      ["popup", "dialog", "alert", "confirm", "prompt", "modal dialog"],
    "upload":     ["upload", "file", "attach", "chooser", "drag and drop file"],
    "download":   ["download", "save", "export", "save as"],
    "tab":        ["new tab", "opens tab", "window", "link opens"],
    "iframe":     ["iframe", "frame", "embed", "nested frame"],
    "shadow_dom": ["shadow", "web component", "custom element"],
    "dropdown":   ["select", "dropdown", "option", "autocomplete", "typeahead"],
    "dynamic":    ["react", "angular", "spa", "loading", "skeleton", "dynamic"],
    "keyboard":   ["press", "key", "shortcut", "ctrl", "keyboard", "tab navigation"],
    "scroll":     ["scroll", "infinite scroll", "load more", "scroll to"],
    "auth":       ["login", "auth", "session", "storage state", "credentials"],
    "network":    ["api", "network", "request", "response", "intercept", "mock"],
    "mobile":     ["mobile", "responsive", "touch", "device", "viewport"],
    "console":    ["console", "js error", "browser error", "page crash"],
    "trace":      ["trace", "replay", "record session", "debug trace"],
    "exploration":["explore", "understand page", "analyze", "what is on this page"],
    "codegen":    ["generate", "write script", "create test", "generate code"],
    "debugging":  ["failed", "error", "broken", "fix", "debug", "not working", "timeout"],
    "screenshot": ["screenshot", "capture", "visual", "take screenshot"],
}

def build_system_prompt(intent: str, context: dict) -> str:
    prompt = read_skill("core")              # always first
    intent_lower = intent.lower()
    
    for skill_name, triggers in SKILL_TRIGGERS.items():
        if skill_name == "core":
            continue
        if triggers and any(t in intent_lower for t in triggers):
            prompt += "\n\n" + read_skill(skill_name)
    
    # inject persistent context
    prompt += "\n\n" + context.get("locator_library", "")
    prompt += "\n\n" + context.get("page_map", "")
    prompt += "\n\n" + context.get("memory", "")
    
    return prompt
```

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

## 12. Memory & Persistence

Three levels of memory. Each serves a different purpose.

### Level 1 — Within-run memory (messages[] list)

Scope: One agent run (one set of steps submitted in LLM mode)

```python
messages = []  # grows as tools are called
# Cleared when a new run starts
# LLM sees complete history of current run
```

Used for: knowing what locators were tried, what failed, what the current page state is.

### Level 2 — Session memory (Python objects)

Scope: One session (from launch to exit)

```python
session = {
    "run_id": "...",
    "steps": [],          # recorded steps
    "current_url": "",
    "domain": "",
    "locators": {},       # locators found this session
    "page_maps": {},      # pages explored this session
}
```

Used for: step list, current state, locators found during this session.

### Level 3 — Persistent memory (files)

Scope: Across sessions

**Locator library** — `.hermes/locators/[domain].json`
```json
{
  "app.example.com": {
    "login-page": {
      "email-input":    "getByLabel('Email')",
      "password-input": "getByLabel('Password')",
      "login-button":   "getByRole('button', {name: 'Login'})"
    },
    "dashboard": {
      "heading": "getByRole('heading', {name: 'Dashboard'})"
    }
  }
}
```

When a session starts, the locator library for the current domain is injected into the LLM system prompt. The LLM reuses known locators instead of re-discovering them.

**Page maps** — `.hermes/page-maps/[domain]/[path-hash].json`
```json
{
  "url": "https://app.example.com/results",
  "explored_at": "2026-04-30T10:00:00Z",
  "sections": { ... },
  "summary": "Results page with filter bar, data table, pagination"
}
```

**Session memory** — `.hermes/memories/MEMORY.md`
```
# Memory — app.example.com

## Locator patterns that work
- Login button: getByRole('button', {name: 'Login'}) — always stable
- Email input: getByLabel('Email') — stable

## Patterns that failed
- data-testid='login-btn' changed to data-testid='btn-login' on 2026-04-15

## App behavior notes
- After login, redirects to /dashboard with 1-2s delay
- Filter bar requires waitForLoadState('networkidle') after each change
```

**Error patterns** — `.hermes/memories/error-patterns.json`
```json
{
  "Element not interactable": {
    "seen_count": 12,
    "best_fix": "scroll into view then retry",
    "success_rate": "91%"
  },
  "Timeout exceeded": {
    "seen_count": 8,
    "best_fix": "waitForLoadState networkidle",
    "success_rate": "88%"
  }
}
```

When an error occurs, the system checks error patterns first and tries the best known fix immediately.

**Auto-update after every session:**
- Confirmed locators → saved to locator library
- New fix patterns → saved to error patterns
- App behavior notes → appended to MEMORY.md

---

## 13. The Overlay UI

### Injection method

```python
# In PanelBridge startup:
# 1. Start local aiohttp server (panel HTML + WebSocket)
# 2. Inject iframe via add_init_script
# 3. Reinject on every page load event

async def inject_panel(page: Page):
    port = self.port
    inject_js = f"""
    (function() {{
        if (document.getElementById('__copilot_panel_host')) return;
        const iframe = document.createElement('iframe');
        iframe.id = '__copilot_panel_host';
        iframe.src = 'http://127.0.0.1:{port}/panel';
        iframe.style.cssText = `
            position: fixed;
            top: 0;
            right: 0;
            width: 380px;
            height: 100vh;
            border: none;
            z-index: 999999;
            background: transparent;
        `;
        document.body.appendChild(iframe);
    }})();
    """
    await page.add_init_script(inject_js)
    # also reinject on load events for navigation resilience
    page.on('load', lambda: asyncio.create_task(page.evaluate(inject_js)))
```

### Panel layout

```
┌────────────────────────────────────────────────────┐
│ ⚡ CO-PILOT  [Manual ▼] [LLM ▼]  [⋮] [━][□][✕]    │
├────────────────────────────────────────────────────┤
│ TOOLBAR:                                           │
│ [🔍 Pick] [✨ Highlight] [📸 Screenshot] [🌐 Net]  │
│ [⏸ Pause] [⏹ Stop] [▶ Continue] [⏭ Skip]         │
├────────────────────────────────────────────────────┤
│ TABS:                                              │
│ [📋 Steps] [💻 Code] [🔍 Locator] [🌐 Network]    │
├────────────────────────────────────────────────────┤
│                                                    │
│  [TAB CONTENT AREA]                                │
│                                                    │
│  Steps tab:   ordered step list with controls      │
│  Code tab:    live TypeScript preview              │
│  Locator tab: locator inspector results            │
│  Network tab: captured API calls                   │
│                                                    │
├────────────────────────────────────────────────────┤
│ CHAT INPUT (LLM mode):                             │
│ [Type intent or /command...          ] [Send]      │
│ [📎 Attach] [/commands] [📋 Cheat Sheet]           │
└────────────────────────────────────────────────────┘
```

### Docking options

- **Right** (default) — page shrinks to fill remaining width
- **Left** — page margin-left offset
- **Bottom** — page height reduces
- **Detached** — floating, draggable, page restores full size

### Element picker technical flow

```
User clicks [🔍 Pick] in toolbar
        ↓
Panel sends: { type: "pick_start" }
        ↓
Backend sets: window.__agentPickIntent = true
Injects pick helper JS:
  document.addEventListener('mouseover', captureHover)
  document.addEventListener('click', captureClick, true)
  cursor changes to crosshair
        ↓
User moves mouse:
  captureHover fires on each element
  Reads: tag, id, class, role, aria-label,
         data-testid, text, bounding box
  Draws blue outline using getBoundingClientRect()
        ↓
User clicks element:
  captureClick fires
  Outline turns green — LOCKED
  Mouse events restored
  Pick mode ends
        ↓
Backend receives element descriptor
Runs LocatorEngine.rank_candidates(descriptor)
Returns top 5 locator candidates with scores
        ↓
Panel shows:
  Selected element: [Login button]
  Best locator: getByRole('button', {name: 'Login'}) ✅ 90%
  Alternatives: [data-testid='login-btn'] [#login-button]
```

### Visual feedback states

| State | Visual |
|---|---|
| Hovering element | Blue outline (2px solid #4A9EF5) |
| Element selected | Green solid outline (#22C55E) |
| Locator searching | Pulsing yellow (#EAB308) |
| Locator validated ✅ | Green glow + checkmark |
| Locator failed ❌ | Red glow → auto self-correct starts |
| Agent correcting | Orange glow (#F97316) |
| Assertion added | Purple marker (#A855F7) |
| Step recorded | Brief green flash (0.5s) |

### Step panel — per step

Each step in the panel shows:
```
[▶] [✏️] [🗑] [⬆] [⬇] [+ After] [📝 Note]
3. ✅ Click [Login button]
   Locator: getByRole('button', {name: 'Login'})
   Strategy: aria role + name (stable ✅)
   ▶ expand for alternatives
```

Step actions:
- **[▶ Run]** — run this step only, validate right now
- **[✏️ Edit]** — edit action, locator, value, timeout
- **[🗑 Delete]** — remove from step list (browser state unchanged)
- **[⬆][⬇]** — reorder (drag also supported)
- **[+ After]** — insert new step after this one
- **[📝 Note]** — add annotation (appears as comment in code)

### Quick commands

```
/replay      → replay all recorded steps
/generate    → generate TypeScript script now
/save        → save session to file
/load        → load previous session
/versions    → show saved versions
/clear       → clear all recorded steps
/status      → show all recorded steps
/save-auth   → save browser storage state
/load-auth   → load saved storage state
/locators    → show locator library for this domain
/explore     → explore current page and build page map
/network     → show captured network calls
/screenshot  → take screenshot of current page
```

---

## 14. WebSocket Protocol

All messages are JSON. Direction: → = Panel to Backend, ← = Backend to Panel.

### Panel → Backend

| Message | Payload | Description |
|---|---|---|
| `pick_start` | `{}` | Start element pick mode |
| `pick_cancel` | `{}` | Cancel pick mode |
| `append_step` | `{ action, locator, params, mode }` | Add step to session |
| `validate_step` | `{ action, locator, params, stepId? }` | Validate one step live |
| `run_step` | `{ stepId }` | Run single step |
| `replay` | `{ startIndex?, stopOnError? }` | Replay all/partial steps |
| `pause_replay` | `{}` | Pause after current action |
| `resume` | `{ overrideLocator?, overrideParams? }` | Resume from pause |
| `stop_replay` | `{}` | Hard stop |
| `skip_step` | `{ stepId }` | Skip current/specified step |
| `llm_run` | `{ steps[], mode }` | Submit steps to LLM agent |
| `llm_cancel` | `{}` | Cancel running LLM agent |
| `force_fix` | `{ stepId }` | Trigger repair cascade for step |
| `llm_assist` | `{ stepId, maxIterations? }` | LLM repair for step |
| `delete_step` | `{ stepId }` | Delete step |
| `edit_step` | `{ stepId, action, locator, params }` | Edit step |
| `insert_step` | `{ index, action, locator?, params? }` | Insert step at position |
| `reorder_step` | `{ stepId, newIndex }` | Reorder step |
| `save_version` | `{ name, stepIds? }` | Save named version |
| `load_version` | `{ name }` | Load named version |
| `list_versions` | `{}` | List all saved versions |
| `delete_version` | `{ name }` | Delete named version |
| `start_recording` | `{}` | Start auto-recording mode |
| `stop_recording` | `{}` | Stop auto-recording mode |
| `get_code` | `{ format? }` | Request generated TypeScript |
| `save_to_file` | `{ path? }` | Save session JSON to default location |
| `save_as_file` | `{ path, name }` | Save session JSON to custom path/name |
| `save_copy` | `{ path, name }` | Save a copy, continue on original |
| `load_from_file` | `{ path? }` | Load session JSON (recent list or browse) |
| `load_from_path` | `{ path }` | Load session from specific filesystem path |
| `set_mode` | `{ mode: "manual"\|"llm" }` | Switch mode |
| `set_llm_config` | `{ provider, model, api_key, base_url }` | Configure LLM |

### Backend → Panel

| Message | Payload | Description |
|---|---|---|
| `ready` | `{ runId, mode, llmStatus, domain }` | Session ready |
| `pick_result` | `{ locator, candidates[], element, framePath? }` | Element picked + locators ranked |
| `pick_cancelled` | `{}` | Pick cancelled |
| `step_list` | `{ steps[] }` | Full current step list |
| `step_status` | `{ stepId, status, error? }` | Single step status update |
| `validate_result` | `{ passed, error?, friendlyError?, durationMs }` | Validation result |
| `replay_status` | `{ running, currentIndex?, paused?, error? }` | Replay progress |
| `llm_thinking` | `{ message }` | LLM working — show to user |
| `llm_tool_call` | `{ tool, args }` | LLM called a tool — show progress |
| `llm_result` | `{ success, summary, stepsUpdated[] }` | LLM run complete |
| `force_fix_progress` | `{ stage, detail?, attempts? }` | Repair in progress |
| `force_fix_result` | `{ success, locator?, reason?, attempts[] }` | Repair complete |
| `llm_assist_progress` | `{ iteration, attempt, strategy }` | LLM repair progress |
| `llm_assist_result` | `{ success, patch?, attempts[] }` | LLM repair complete |
| `highlight_element` | `{ boundingBox, state }` | Draw highlight at coords |
| `clear_highlight` | `{}` | Remove all highlights |
| `code_result` | `{ content, format }` | Generated TypeScript code |
| `step_recorded` | `{ step }` | New step confirmed and saved |
| `session_saved` | `{ path, name }` | Session file saved — shows path to user |
| `session_loaded` | `{ stepCount, path, name }` | Session file loaded |
| `version_saved` | `{ name }` | Version snapshot saved |
| `version_loaded` | `{ name, stepCount }` | Version loaded |
| `versions_list` | `{ versions[] }` | List of saved versions |
| `network_capture` | `{ calls[] }` | Network calls captured |
| `suggestion` | `{ message, actions[] }` | Smart suggestion from agent |
| `error` | `{ message, detail?, code? }` | Error with typed code |

---

## 15. Session Management

### One session = one output file

```
Session start:
  Backend asks (or auto-detects from first URL):
  "What are we testing today?"
  Answer → test name + file name

Auto-naming format:
  .hermes/output/[YYYY-MM-DD]-[session-name].spec.ts
  Example: 2026-04-30-login-flow.spec.ts

Session JSON (for reload/replay):
  .hermes/output/[YYYY-MM-DD]-[session-name].session.json
  {
    "name": "login flow",
    "url": "https://app.example.com",
    "date": "2026-04-30",
    "steps": [...],
    "locators": {...}
  }
```

### Save options

```
[💾 Save]
  → Saves to default auto-named location
  → .hermes/output/[date]-[name].spec.ts
  → Overwrites if file already exists

[💾 Save As]
  → User picks custom name + custom folder
  → Can save to any location on disk:
    ~/tests/smoke/login.spec.ts
    ~/projects/myapp/tests/login.spec.ts
  → Both .spec.ts and .session.json saved together
  → Panel shows save dialog:
    Name: [login-flow          ]
    Path: [.hermes/output/     ] [Browse]
    [Save] [Cancel]

[📋 Save Copy]
  → Save a copy to new location
  → Continue working on original session
  → Useful for checkpointing
```

### Load options

```
[📂 Load Recording]
  → Shows recent recordings list:
    📄 login-flow       2026-04-30  12 steps  ✅
    📄 checkout-flow    2026-04-29   8 steps  ❌
    📄 settings-update  2026-04-28  15 steps  ✅
    [Search recordings...]
    [Browse for file...]

  User can:
  → Pick from recent list (loaded from .hermes/output/)
  → Browse filesystem for any .session.json anywhere
  → Load any past recording from any location

  After load:
    Steps loaded into step panel
    Browser navigates to session's starting URL
    User decides: [▶ Replay] or [Continue adding steps]
    Steps loaded but NOT auto-executed

[📂 Load from path]
  → User types or pastes path directly:
    /load ~/Downloads/old-test.session.json
    /load ~/projects/myapp/tests/checkout.session.json
```

### Version snapshots

At any point the user can save a named version:
```
/versions → save version "before-assertions"
Later: /versions → load version "before-assertions"
Stored in SQLite — not just files
```

### Step management rules

- **Add step** → appended to list. Browser state unchanged.
- **Delete step** → removed from list only. Browser stays at current state.
- **Edit step** → modified in list. Re-validated immediately.
- **Reorder step** → reordered in list. No re-execution.
- **None of these operations re-execute in browser unless user explicitly asks.**

### Auto-save

Session auto-saves to `.session.json` after every confirmed step. If user force-quits, nothing is lost. Last state is always recoverable.

### Parallel sessions

```
Terminal 1 → session 1 → browser 1 → file 1
Terminal 2 → session 2 → browser 2 → file 2
No shared state. No interference.
```

---

## 16. Data Input Methods

| Method | How | Example |
|---|---|---|
| **Plain text in chat** | Type directly | "fill email with test@example.com" |
| **Environment variables** | `.hermes/.env` (gitignored) | "use credentials from env" → reads `TEST_EMAIL` |
| **File drop zone** | Drop file in `.hermes/uploads/` | "use the resume in uploads" |
| **JSON test data** | `.hermes/test-data/data.json` | "use user data from test data file" |
| **Direct file path** | Type path | "upload the file at ~/Documents/resume.pdf" |
| **Auto-generated (Faker)** | No data provided | "fill name field" → `faker.person.fullName()` |

**Faker behavior:**  
Agent always tells user what it generated. Never uses Faker silently.  
"I used: generated-email@example-faker.com"

**Secrets rule:**  
Values from `.env` are NEVER shown in chat, logs, or generated code.  
Generated code references env var names, not values:
```typescript
await emailInput.fill(process.env.TEST_EMAIL ?? '')
await passwordInput.fill(process.env.TEST_PASSWORD ?? '')
```

---

## 17. Authentication & Storage State

**User controls auth completely. Agent never touches it unless explicitly asked.**

```
FLOW 1 — First time setup:
  User logs in manually in browser
  User says: "save storage state" or /save-auth
  Agent saves:
    await context.storageState({
      path: '.hermes/auth/storageState.json'
    })
  Confirms: "Storage state saved ✅"

FLOW 2 — Every session after:
  User says: "load auth" or /load-auth
  Agent creates context with saved state:
    browser.newContext({
      storageState: '.hermes/auth/storageState.json'
    })
  Navigate → already logged in ✅

FLOW 3 — Auth expires:
  Agent detects: redirect to login OR 401 response
  Tells user: "Auth expired — please log in again"
  User logs in → agent saves new state → continues

FLOW 4 — No auth needed:
  User never mentions auth
  Agent never touches it

MULTIPLE USERS:
  .hermes/auth/admin-storageState.json
  .hermes/auth/user-storageState.json
  User specifies which to load explicitly
```

---

## 18. Output — Generated Code

### Structure

```typescript
// ============================================
// Generated by Playwright Co-pilot
// Session: 2026-04-30T10:00:00Z
// App: https://app.example.com
// Test: login flow
// ============================================

import { test, expect } from '@playwright/test'

// === LOCATORS ===
// All locators defined here for easy maintenance
// Update locators here when app changes

const emailInput    = page.getByLabel('Email')
const passwordInput = page.getByLabel('Password')
const loginButton   = page.getByRole('button', { name: 'Login' })
const dashboard     = page.getByRole('heading', { name: 'Dashboard' })

// ⚠ Fragile locator — no stable attributes found
// Consider adding data-testid to this element
const submitBtn = page.locator('//form/div[3]/button')

// === TEST ===
test('login flow', async ({ page }) => {
  await page.goto(process.env.BASE_URL ?? 'https://app.example.com')
  await emailInput.fill(process.env.TEST_EMAIL ?? 'test@example.com')
  await passwordInput.fill(process.env.TEST_PASSWORD ?? '')
  await loginButton.click()
  await expect(dashboard).toBeVisible()
})
```

### Why locators at the top

- Easy to update when app changes
- Clear separation from test logic
- Standard pattern every Playwright engineer knows
- One place to fix when locators break

### Auto-generated Playwright config (if missing)

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: '.hermes/output',
  timeout: 30000,
  retries: 1,
  reporter: [
    ['html', { outputFolder: '.hermes/reports' }],
    ['list']
  ],
  use: {
    baseURL: process.env.BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } }
  ]
})
```

---

## 19. Features Scope — v1

### Must have (v1 required)

| # | Feature | Description |
|---|---|---|
| 1 | **Manual Mode** | Full Playwright vocabulary, element picker, dropdown action selector, immediate validation |
| 2 | **LLM Mode** | Plain English steps, full LLM agent loop, all actions handled automatically |
| 3 | **Locator Engine** | 11-strategy programmatic waterfall + LLM fallback, confidence scoring |
| 4 | **Validation** | Immediate live validation on every step, unified pipeline |
| 5 | **Recovery Loop** | 4-stage repair cascade, LLM fallback, human escalation as last resort |
| 6 | **Live Code View** | TypeScript updating in real time as steps are added |
| 7 | **Replay** | Full replay with auto-fix, per-step replay, range replay |
| 8 | **Save/Load Sessions** | Save `.spec.ts` + `.session.json`, load and continue |
| 9 | **Version Snapshots** | Named versions in SQLite, save/load/delete |
| 10 | **Pause/Stop/Continue/Skip** | Full execution controls at any time |
| 11 | **Persistent Locator Library** | Remembers validated locators across sessions |
| 12 | **Page Maps** | Explore once, store, reuse — zero re-exploration cost |
| 13 | **Session Memory** | MEMORY.md, error patterns — gets smarter every session |
| 14 | **Skills System** | 24 SKILL.md files loaded contextually into LLM prompts |
| 15 | **Overlay Panel** | Iframe injection, docking, element picker, highlight layer |
| 16 | **Auth State Management** | Save/load storage state, multi-user support |
| 17 | **Step Management** | Add/edit/delete/reorder steps without re-executing |
| 18 | **Locator Inspector** | Inspect any element's locator options without recording |

### Should have (v1 if time, v2 otherwise)

| # | Feature | Description |
|---|---|---|
| 19 | **Self-healing Tests** | When replay fails due to locator change, auto-find new locator |
| 20 | **Assertion Builder** | Visual guided assertion creation in panel |
| 21 | **Network Capture Panel** | View/filter captured API calls, generate assertions and mocks |
| 22 | **Smart Suggestions** | Proactive suggestions after actions (save auth, add assertion) |

### Deferred (v2+)

Exploration mode (full systematic), Debug mode, Accessibility testing, Test parameterization, Test tagging/filtering, Import existing tests, Visual diff/baseline screenshots, Smart wait analyzer, Test diff viewer, Annotations on steps.

---

## 20. The 10 Hard Rules

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

## 21. What to Keep from Existing Codebase

These components are solid, async-native, and should be used as-is:

| Component | File | Reason to keep |
|---|---|---|
| `BrowserSession` | `execution/browser.py` | Reliable async Playwright browser lifecycle |
| `ToolRuntime` | `execution/tools.py` | Complete Playwright action vocabulary, all edge cases |
| `StepGraphRunner` | `execution/runner.py` | Step loop with retries, events, checkpoints |
| `LocatorEngine` | `locator/engine.py` | Multi-strategy ranking with confidence scoring |
| `StepGraph models` | `stepgraph/models.py` | Clean data model for steps |
| `force_fix` | `healing/force_fix.py` | 4-stage repair cascade — exactly what we designed |
| `llm_assist` | `healing/llm_assist.py` | Multi-attempt LLM repair with history |
| `LLMOrchestrator` | `llm/orchestrator.py` | The tool-calling loop — wire it to the panel |
| LLM providers | `llm/openai.py`, `llm/anthropic.py`, `llm/openai_compatible.py` | Provider abstraction is correct |
| `LLMContext` tiered builder | `llm/context.py` | Tiered DOM/context escalation — refine and use |
| Storage repos | `storage/repos/*.py` | SQLite persistence is solid |
| DB migrations | `storage/migrations/*.sql` | Keep schema, run migrations cleanly |

---

## 22. What to Rebuild

These components have fundamental problems and must be rebuilt:

| Component | Problem | Rebuild as |
|---|---|---|
| Panel protocol | No typed schema, frontend/backend drift, `openUploadFix` not defined | Typed message contract (Section 14), strict schema validation |
| Validation pipeline | Panel validate and runner validate have different behavior | One unified validation path: all validation goes through ToolRuntime |
| LLM mode architecture | 3 separate disconnected paths (`force_fix`, `llm_assist`, `llm_build_step`) | One `LLMAgentLoop` class connected to `LLMOrchestrator` |
| Execution path | Panel replay, runner replay, dashboard replay, orchestrator — all doing different things | One canonical path: Panel → PanelBridge → single execution handler |
| `agent ui` dashboard | Duplicates panel functionality, adds complexity | Remove or fold into panel |
| Panel frontend (panel.html) | Prototype quality, no state management, missing handlers | Clean rebuild with typed state, typed WebSocket contract |
| Config/security | API keys in plaintext `~/.agent/llm_config.json` | Env vars only, never persist keys to disk |
| Platform coupling | macOS-only file picker (AppleScript) | Cross-platform solution |

---

## 23. Folder Structure

```
.hermes/
  ├── auth/
  │   ├── storageState.json          ← default user auth
  │   ├── admin-storageState.json
  │   └── user-storageState.json
  │
  ├── uploads/                       ← user drops files here
  │
  ├── output/                        ← generated test files
  │   ├── 2026-04-30-login-flow.spec.ts
  │   └── 2026-04-30-login-flow.session.json
  │
  ├── traces/                        ← auto-deleted on pass
  │   └── session-id.zip
  │
  ├── test-data/
  │   └── data.json
  │
  ├── locators/
  │   └── app-example-com.json       ← persistent locator library
  │
  ├── page-maps/
  │   └── app-example-com/
  │       └── login-page.json        ← explored page structures
  │
  ├── reports/
  │   └── index.html
  │
  ├── skills/
  │   └── playwright-automation/
  │       ├── core/SKILL.md          ← human editable only
  │       └── [24 skill files]
  │
  ├── memories/
  │   ├── MEMORY.md                  ← persistent facts
  │   ├── USER.md                    ← user preferences
  │   └── error-patterns.json        ← known fixes
  │
  ├── .env                           ← secrets (gitignored)
  │   BASE_URL=https://staging.example.com
  │   TEST_EMAIL=user@company.com
  │   LLM_API_KEY=sk-...
  │   LLM_BASE_URL=https://api.openai.com/v1
  │   LLM_MODEL=gpt-4o
  │
  ├── .hermesignore                  ← files agent never touches
  │   node_modules/
  │   .git/
  │   *.secret
  │   *.pem
  │   *.key
  │
  └── config.yaml                    ← co-pilot configuration
```

---

## 24. Build Order

Build in this order. Each phase is independently testable.

### Phase 1 — Core execution (Week 1-2)

Goal: Browser opens, overlay appears, element picker works, manual mode validates a click.

1. Port/clean `BrowserSession` + `ToolRuntime` from existing codebase
2. Rebuild `PanelBridge` with typed WebSocket schema
3. Rebuild `panel.html` with clean state management
4. Wire: pick_start → element descriptor → locator candidates → panel display
5. Wire: validate_step → ToolRuntime → validate_result
6. Wire: append_step → step list → code view updates

**Acceptance test:** User opens browser, picks a button, system finds locator, validates it, records step, code view shows TypeScript.

### Phase 2 — Manual mode complete (Week 3)

Goal: All Playwright actions work in manual mode.

1. Full action dropdown (all actions from Section 8)
2. Special case auto-detection (popup, new tab, iframe, upload, dropdown)
3. Recovery loop for manual mode failures
4. Replay with pause/stop/continue/skip
5. Save/load sessions

**Acceptance test:** User records a complete login flow manually. Replays it. One step fails. System auto-fixes. All steps pass.

### Phase 3 — LLM mode (Week 4-5)

Goal: User describes steps in plain English, LLM handles everything.

1. Wire `LLMOrchestrator` to `PanelBridge` as the LLM agent loop
2. Build skills system (24 SKILL.md files, contextual loading)
3. Build DOM strategy (adaptive snapshot, page maps, token measurement)
4. Build tool registry (all tools from Section 9)
5. Build messages[] context management
6. Wire send_to_panel as a registered tool
7. LLM persona + system prompt

**Acceptance test:** User says "go to login page, fill email with test@test.com, click login, assert dashboard is visible." LLM handles all of it including locator finding and validation.

### Phase 4 — Memory & persistence (Week 6)

Goal: System gets smarter every session.

1. Locator library — save and inject on session start
2. Page maps — explore once, store, reuse
3. MEMORY.md — update after every session
4. Error patterns — build and use fix history
5. Version snapshots — save/load named versions

**Acceptance test:** Session 1 finds locators from scratch. Session 2 for the same app reuses all known locators. Zero re-discovery.

### Phase 5 — Polish & remaining features (Week 7-8)

1. Self-healing tests during replay
2. Assertion builder in panel
3. Network capture panel
4. Locator inspector tool
5. Smart suggestions
6. Cross-platform file picker (replace AppleScript)
7. Security hardening (remove plaintext key storage)

---

*End of PRD v2*
