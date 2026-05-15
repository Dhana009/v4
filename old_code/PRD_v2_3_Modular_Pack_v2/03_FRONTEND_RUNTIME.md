# 03 — Frontend Runtime

> PRD v2.3 modular pack. Existing PRD v2.2 wording is preserved where it still applies. New or corrected material is marked as v2.3 guidance.


## v2.3 frontend architecture decision

AutoWorkbench UI is now a real frontend source tree, not a giant string inside `browser.py`.

Target flow:

```text
frontend/ source
→ build JS/CSS
→ frontend/dist/autoworkbench.js + autoworkbench.css
→ browser.py injects built assets
→ window.AutoWorkbench.mount(root, config)
```

`browser.py` is the injector/bootstrapper. It should not own product UI logic.

## Docked panel architecture

The final UI should behave like DevTools/Inspect:

```text
dock right
dock left
dock bottom
floating
hidden
resizable
fullscreen-safe
```

Important distinction:

```text
Shadow DOM = CSS isolation
Docked layout host = page content is not covered
Resize handling = user controls panel size
Fullscreen/window policy = no white gutters or broken viewport
```

### Docking stages

| Stage | Approach | Purpose |
|---|---|---|
| MVP | injected AutoWorkbench panel | current working path |
| Stabilized | Shadow DOM + docked layout host | isolate UI and prevent page content being covered |
| Later | optional separate window or extension | packaging/productization only if needed |

### Docked layout rules

- Docked right: tested page content area compensates for panel width.
- Docked left: tested page content area compensates for panel width.
- Docked bottom: tested page content area compensates for panel height.
- Floating: panel may overlay content, but this is an explicit user choice.
- Hidden: panel removed/collapsed and page restored.
- Resize: dragging panel edge updates compensation live.
- Fullscreen: panel and page resize cleanly; no white gutters/borders caused by viewport mismatch.

### Expected criteria

- In docked mode, target page content is not hidden behind the panel.
- User can resize the panel and the page adjusts immediately.
- Fullscreen and normal window modes both render without white gutters caused by the panel.
- Floating mode is optional and clearly different from docked mode.


## Frontend interaction modes

The UI must not mix plan, clarification, and recovery.

```text
idle
drafting
plan_review
clarification
executing
recovery
completed
```

### Mode behavior

| Mode | Shows | Allowed user actions |
|---|---|---|
| idle | ready state | add step, load session, start recording |
| drafting | pending step editor | add/delete/reorder pending steps, attach element |
| plan_review | proposed plan | Confirm Plan, Send Correction |
| clarification | exact agent question | Send Answer, choose option |
| executing | live progress | pause/stop; editing disabled |
| recovery | failure summary + LLM diagnosis | Send Recovery Instruction, Skip Step, Stop Run |
| completed | summary + recorded output | replay, save, generate/export |

### Expected criteria

- Confirm Plan is never shown in clarification mode.
- Clarification displays the exact backend question, not a generic placeholder.
- Recovery displays failure reason, current URL, tried fixes, and next requested user input.
- All mode transitions are caused by typed backend events or explicit user commands.


## UX feedback rules

The UI must explain state, not only log text.

Every important backend state should have visible feedback:

```text
thinking
planning
validating
executing
recovering
recorded
failed
skipped
code updated
saved
replayed
```

No generic `Unknown error` should be shown if structured error data exists.

### Expected criteria

- User can tell what is happening at all times without reading terminal logs.
- Every failure shows a friendly summary plus expandable technical detail.
- Recorded output explains what happened before showing raw locator/code metadata.


## Agent Control Center

The UI must expose multi-agent visibility and controls. Users should know which model-backed agent is working, why it activated, and whether it can be disabled.

### Required agent visibility

```text
Main Orchestrator       required in LLM Mode
Page Intelligence       optional; nano model page/DOM/locator understanding
Debug Agent             optional; specialized failure diagnosis
Codegen Reviewer        optional; reviews deterministic codegen in complex cases
Judge/Risk Agent        optional later; high-risk/destructive action review
Step Runner             system runtime; cannot disable
```

### Required controls

| Control | Expected behavior |
|---|---|
| Toggle Page Intelligence Agent | Enables/disables nano page intelligence. If disabled, fallback to deterministic extraction + main model. |
| Toggle Debug Agent | Enables/disables specialist debug model. If disabled, main model handles recovery. |
| Toggle Codegen Reviewer | Enables/disables model-based code review. Deterministic codegen still runs. |
| Run Page Intelligence Now | Builds/refreshes page intelligence for current page or selected section. |
| Clear Page Intelligence Cache | Clears cached page intelligence for current URL/section. |
| Show Agent Trace | Displays recent agent calls, reason, model, tokens, cost, latency, and summary. |

### Expected criteria

- User can see active/running/idle/disabled state for each optional agent.
- Agent activity is shown through typed backend events, not inferred from logs.
- Main Orchestrator and Step Runner cannot be disabled while LLM Mode is running.
- Agent traces do not expose secrets or full raw DOM by default.
- Disabling optional agents must not break core LLM Mode; it only changes quality/cost behavior.


---

> **Preserved v2.2 reference only.** If this section conflicts with v2.3 guidance above, v2.3 wins.

## Preserved v2.2 overlay UI section

### Injection method

MVP uses a direct injected in-page overlay. The panel is inserted into the live page DOM and connects to the backend over WebSocket.

```python
async def inject_panel(page: Page):
    # 1. Inject overlay host and isolated CSS/JS
    # 2. Connect overlay to ws://localhost:PORT/ws
    # 3. Reinject after navigation if the page reloads
    # 4. Keep picker events coordinated with the live DOM
    await page.add_init_script(panel_bootstrap_js)
    await page.evaluate(panel_bootstrap_js)
```

#### Overlay evolution

| Stage | Approach | Decision |
|---|---|---|
| MVP | Direct in-page overlay | Current approach; fastest for picker + WebSocket + live logs |
| Stabilized | Shadow DOM overlay | Better CSS/layout isolation while preserving page access |
| Future product | Chrome extension or separate control panel | Better packaging, but not needed for current LLM Mode MVP |
| Avoid for MVP | iframe overlay | CSP/cross-origin/picker complexity makes it fragile |

The panel must use strong CSS scoping today and should move to Shadow DOM once LLM Mode is stable enough to justify UI hardening.

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