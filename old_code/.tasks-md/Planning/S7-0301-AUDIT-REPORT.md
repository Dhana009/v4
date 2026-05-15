# S7-0301 Frontend Architecture Audit Report

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0301  
**Date:** 2026-05-13  
**Auditor:** Cluster 3 implementation pass  

---

## 1. Entry Point and Shadow DOM Host

**File:** `frontend/src/main.jsx` (3087 lines — monolith risk)  
**Build command:** `esbuild src/main.jsx --bundle --platform=browser --format=iife --outfile=dist/autoworkbench.js`  

Shadow DOM setup (lines ~129–176):
```
SHADOW_HOST_ID    = "aw-shadow-host"
SHADOW_MOUNT_ID   = "aw-shadow-mount"
SHADOW_STYLE_ID   = "aw-shadow-style"

ensureShadowHost(host) → host.attachShadow({ mode: "open" })
ensureShadowMount(shadowRoot) → createElement("div") with data-testid="aw-shadow-mount"
ensureShadowStyles(shadowRoot) → clones #autoworkbench-style into shadow root
```

Mounting (lines ~3044–3087):
- `mount(root, config)` → `resolveMountNode()` → `renderInto(node, config)`
- `renderInto` attaches Shadow DOM, creates React root, renders `<AutoWorkbenchRuntime>`
- Exposes `window.AutoWorkbench = { mount, unmount, remount, version }`

---

## 2. Transport and Event Receiver

**Hook:** `useAutoWorkbenchTransport(config)` (line 1732) delegates to `useAutoWorkbenchTransport`  
**WebSocket:** `new WebSocket(wsUrl)` inside `useEffect` (line ~2860)  
**Event handler:** `socket.onmessage → normalizeBackendMessage() → handleBackendMessage()`  
**URL resolution:** `resolveWsUrl(config)` tries config overrides → `ws://localhost:8765/ws` default  

Backend message dispatch (line ~1800–2000): event `type` field routes to handlers:
- `plan_ready`, `plan_started` → setPlan
- `step_recorded` → setRecordedSteps
- `run_completed` → setRunState
- `status`, `log` → appendTimeline
- `clarification_needed` → setClarificationQuestion
- `recovery_needed` → setRecoveryText
- etc.

---

## 3. IDEPanel Props and State Threading

**IDEPanel loaded via:** `const IDEPanel = window.IDEPanel;` (line 2997)  
**Registered by:** `frontend/aw-ide-panel.jsx` (2135 lines) side-effect import  

Props passed to IDEPanel (line ~3022–3031):
```js
<IDEPanel
  state={panelState}          // "idle"|"planning"|"await"|"exec"|"recover"|"done"
  tab={tab}                   // "workbench"|"steps"|"code"|"debug"
  runtime={{
    live: true,
    ...transport,             // All state from useAutoWorkbenchTransport
  }}
  onTabChange={setTab}
/>
```

`transport` includes: `connectionStatus`, `runState`, `conversation`, `timeline`, `traceEntries`, `plan`, `codePreview`, `lastError`, `pendingCommands`, `pendingSteps`, `recordedSteps`, `interactionMode`, `clarificationQuestion`, `recoveryText`, and all command handlers.

---

## 4. Static vs. Live Component List

| File | Lines | Status | Notes |
|------|-------|--------|-------|
| `frontend/src/main.jsx` | 3087 | **Live transport** | Monolith; has WS, state, command handlers |
| `frontend/aw-ide-panel.jsx` | 2135 | **Mostly static/demo** | Imported for side-effect; renders demo data |
| `frontend/aw-tabs.jsx` | 245 | Static demo | Not in production build path directly |
| `frontend/aw-workbench.jsx` | 368 | Static demo | Not imported from main.jsx |
| `frontend/aw-bits.jsx` | 75 | Static demo | Small utility components |
| `frontend/aw-header.jsx` | 77 | Static demo | Standalone header |
| `frontend/design-canvas.jsx` | 789 | Design tool | Not in production |
| `frontend/tweaks-panel.jsx` | 426 | Design tool | Not in production |
| `frontend/aw-pagemock.jsx` | 168 | Mock page | Not in production |

**Static demo data in aw-ide-panel.jsx:** Contains hardcoded plan steps, code snippets, trace entries, recommendation lists as default/fallback values. These render when `runtime` props are absent or in demo mode.

---

## 5. Build Command and Output Structure

```
npm run build
→ esbuild src/main.jsx --bundle --platform=browser --format=iife
→ dist/autoworkbench.js  (1.2 MB)
→ dist/autoworkbench.css (42.9 KB)
```

Build time: ~37ms. No test runner configured in package.json.

**Imported at build time from main.jsx:**
- `../styles.css` → embedded in CSS output
- `../style-ide.css` → embedded in CSS output
- `../icons.jsx` → bundled (registers `window.Icons`)
- `../aw-ide-panel.jsx` → bundled (registers `window.IDEPanel`)

---

## 6. Test Framework and Locations

No JavaScript/Jest/Vitest test configuration exists in `frontend/`. No `__tests__/` directories.  
Backend tests: Python pytest in `tests/` — covers runtime, event contracts, etc.  
Frontend tests: **None currently** — Cluster 3 creates `tests/test_frontend_*.py` (Python subprocess/grep tests).

---

## 7. Monolith Files (>200 lines) with Line Counts

| File | Lines | Split plan |
|------|-------|-----------|
| `frontend/src/main.jsx` | 3087 | **Cluster 3:** Extract to host/, transport/, store/, commands/ modules |
| `frontend/aw-ide-panel.jsx` | 2135 | **Cluster 6–9:** Split into components/shell/, components/llm/, etc. |
| `frontend/design-canvas.jsx` | 789 | Design tool — not in production |
| `frontend/tweaks-panel.jsx` | 426 | Design tool — not in production |
| `frontend/aw-workbench.jsx` | 368 | Demo — will be replaced by components/ |
| `frontend/aw-vercel-panel.jsx` | 299 | Experimental — not in production path |
| `frontend/aw-tabs.jsx` | 245 | Demo — will be replaced by components/shell/TabBar.jsx |

---

## 8. Prototype Structure and Reusable Patterns

**Location:** `frontend_new_design_prototype/`

| File | Purpose | Reusable patterns |
|------|---------|------------------|
| `app.jsx` | Top-level: state machine → panel chrome → tabs | STATE_META structure, dock/collapse logic, tab routing |
| `chrome.jsx` | Header, TabStrip, Footer, NowStrip, CollapsedRail | Header props shape, status map, tab strip layout |
| `llm-tab.jsx` | LLM conversation thread cards | Card component patterns, clarification/recovery/plan card shapes |
| `secondary-tabs.jsx` | Steps, Recorded, Code, Trace tab content | Tab component shapes, empty state patterns |
| `icons.jsx` | SVG icon set (I.Spark, I.Steps, etc.) | Icon naming conventions |
| `styles.css` | Full design system (colors, spacing, typography) | CSS custom property names, component class names |

**Key CSS vars from prototype styles.css (extraction candidates for tokens.css):**
```css
--bg, --bg-card, --bg-tray         /* backgrounds */
--ink, --tx-2, --tx-3, --tx-4     /* text */
--acc, --acc-2                     /* accent colors */
--grn, --red, --yel, --blu        /* status colors */
--br, --br-strong                  /* borders */
--r, --r-lg                        /* border radius */
--font-mono                        /* monospace font stack */
```

---

## 9. Risk Summary

| Risk | Severity | Mitigation |
|------|----------|-----------|
| `main.jsx` 3087-line monolith | **High** | Cluster 3: extract modules; full split in Clusters 4–5 |
| `aw-ide-panel.jsx` 2135 lines with demo data | **High** | Cluster 6–9: replace with components/ using backend events |
| No JS test framework | **Medium** | Python pytest tests verify structure; JS tests in Cluster 4+ |
| Demo data leaks into live mode | **High** | S7-0305: EmptyState fallbacks; no DEMO_ in new modules |
| Shadow DOM style injection fragile | **Medium** | Cluster 4: host/ module stabilizes lifecycle |
| `window.IDEPanel` coupling | **Medium** | Cluster 6: modular import replaces window registration |

---

## Evidence

- Build verified: `npm run build` → success (1.2 MB bundle, 42.9 KB CSS)
- Line counts: verified via `wc -l`
- Tests passing: `tests/test_frontend_build.py` (13 non-slow tests green)
