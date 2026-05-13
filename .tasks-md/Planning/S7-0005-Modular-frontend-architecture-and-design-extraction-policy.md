# S7-0005 — Modular Frontend Architecture and Design Extraction Policy

**Sprint:** Sprint 7
**Cluster:** 0 (Governance)
**Type:** Documentation
**Status:** Planning
**Owner:** Process

---

## Objective

Define the Sprint 7 frontend architecture rules: how `frontend_new_design_prototype/` is used (visual reference only), how production frontend modules are structured, where new logic goes, and how monolith expansion is prevented.

---

## Source Rules

- PRD `03_FRONTEND_RUNTIME.md` v2.3: "AutoWorkbench UI is now a real frontend source tree, not a giant string inside `browser.py`." — modular architecture required
- PRD `03_FRONTEND_RUNTIME.md`: "Frontend renders backend state and collects user input. It must not infer lifecycle state from LLM text."
- PRD `00_MASTER_INDEX.md`: "Code must remain modular. Do not expand monoliths."
- Sprint 7 Cluster 0 Governance: "No expanding monoliths: agent.py, server.py, browser.py, frontend/src/main.jsx, aw-ide-panel.jsx"
- Sprint 6 HANDOFF BUG-S6-FINAL-002: "Frontend Complete LLM UI is contract-only; no real implementation"

---

## Current Known Context

### `frontend_new_design_prototype/` — Visual Reference Only

Inspected files:
- `app.jsx` — prototype application shell
- `chrome.jsx` — window chrome / header
- `icons.jsx` — icon components
- `index.html`, `index-print.html` — prototype HTML shells
- `llm-tab.jsx` — LLM tab prototype
- `print-app.jsx`, `print.css` — print variant
- `secondary-tabs.jsx` — tab bar components
- `styles.css` — prototype styles
- `tweaks-panel.jsx` — tweaks/settings panel
- `v4/` — sub-version of prototype
- `website.jsx` — website view variant

This directory is a design/visual prototype. It contains no WS transport, no live backend event handling, no typed command dispatch. It MUST NOT be imported or used as a runtime dependency.

### `frontend/src/main.jsx` — Current Production Host

- Shadow DOM host/mount setup
- Live WS transport (`WebSocket` with reconnect)
- State management via `useState` hooks
- `normalizeRunState()`, `normalizeInteractionMode()`, `toPanelState()` normalization functions
- `normalizeConfig()` / `DEFAULT_CONFIG`
- WS message handler stub that partially threads into `IDEPanel`
- **Current problem:** Live transport state is NOT fully threaded into `IDEPanel` — UI can fall back to static/demo content

### `frontend/src/aw-ide-panel.jsx` — Current Production Panel

- Main IDE panel component
- Tab switching
- Component rendering per state
- **Current problem:** May contain demo/static state fallbacks that do not come from backend events

---

## Tests First

This is a documentation/policy story. No implementation tests required.

### Verification
- Architecture policy is complete and actionable
- Module split boundaries are defined before Cluster 2 implementation begins
- No Cluster 2–3 story can expand a monolith without referencing this policy

---

## Architecture Policy

### Rule 1: `frontend_new_design_prototype/` Is a Visual Reference Only

- It must never be imported by production code.
- It must never be used as a runtime source of truth for state, data shapes, or event formats.
- Design tokens (colors, spacing, font sizes, border radii) may be extracted into a new `frontend/src/design-tokens.css` or `design-tokens.js` file.
- Component structure (JSX patterns, layout, visual hierarchy) may inspire production component rewrites — but production components must be driven by typed backend event data, not demo state.
- Typography, icons, and layout patterns from the prototype are fair game to extract; data shapes and state management are not.

### Rule 2: No Static Demo State as Runtime Truth

- Production components must receive all dynamic data as props or from the event store.
- Hardcoded arrays, hardcoded step lists, hardcoded plan text, and hardcoded status strings are forbidden in production components.
- A production component with no data (nothing from backend) must render an empty/loading state, not fabricated demo data.

### Rule 3: No Expanding `main.jsx` or `aw-ide-panel.jsx`

- `main.jsx` is the host entry point only. It must not grow to contain:
  - Tab rendering logic
  - Event handler implementations beyond dispatching to the store
  - Component layout decisions
- `aw-ide-panel.jsx` is the panel container only. New tabs and cards go in their own files.
- Maximum acceptable size for `main.jsx`: ~300 lines. If it exceeds this, a split story must be filed.
- Maximum acceptable size for `aw-ide-panel.jsx`: ~300 lines. Same rule.

### Rule 4: Production Module Split

New Sprint 7 frontend modules must follow this boundary:

| Module | Location | Responsibility |
|--------|----------|----------------|
| WS Transport | `frontend/src/transport.js` | WebSocket connection, reconnect, raw message send/receive |
| Event Store | `frontend/src/store.js` | Application state; reducer that maps typed events to state updates |
| Command Dispatcher | `frontend/src/commands.js` | All `send*(command)` functions; no UI code |
| LLM Tab | `frontend/src/tabs/llm-tab.jsx` | LLM chat, plan review, clarification, recovery cards |
| Steps Tab | `frontend/src/tabs/steps-tab.jsx` | Step list, step builder, step status |
| Code Tab | `frontend/src/tabs/code-tab.jsx` | Code preview, export controls |
| Recorded Tab | `frontend/src/tabs/recorded-tab.jsx` | Immutable recorded output |
| Trace Tab | `frontend/src/tabs/trace-tab.jsx` | Event timeline, diagnostics |
| Design Tokens | `frontend/src/design-tokens.css` | Colors, spacing, typography extracted from prototype |
| Plan Card | `frontend/src/cards/plan-card.jsx` | Renders plan_ready payload |
| Recovery Card | `frontend/src/cards/recovery-card.jsx` | Renders recovery_needed payload |
| Clarification Card | `frontend/src/cards/clarification-card.jsx` | Renders clarification_needed payload |
| Step Progress Card | `frontend/src/cards/step-progress-card.jsx` | Renders step_validating / step_executing |
| Run Completed Card | `frontend/src/cards/run-completed-card.jsx` | Renders run_completed payload |

Existing files that may be modified (with discipline):
- `frontend/src/main.jsx` — wiring only: thread live transport/store state into IDEPanel
- `frontend/src/aw-ide-panel.jsx` — split tabs to their own files; reduce to container/router only

### Rule 5: Testable Modules

- Every new frontend module must have its own test file.
- `store.js` reducer must be pure functions — testable without DOM.
- `commands.js` must be pure functions — testable without DOM.
- Tab and card components must accept event payload as props — testable without a real WS.

### Rule 6: Design Token Extraction Protocol

When extracting from `frontend_new_design_prototype/`:

1. Identify color variables, spacing scales, font sizes, and border radii.
2. Create `frontend/src/design-tokens.css` as CSS custom properties (`--aw-color-*`, `--aw-space-*`, etc.).
3. Do not copy component logic, data shapes, or state management.
4. Reference the prototype file in a comment: `/* Extracted from frontend_new_design_prototype/styles.css */`.
5. Production components use the tokens, not hardcoded values.

---

## Forbidden Patterns

The following patterns are forbidden in Sprint 7 frontend implementation:

- `import ... from '../../frontend_new_design_prototype/...'` — any import from prototype
- Hardcoded step arrays in production component files
- Hardcoded plan text or recovery messages in production components
- `if (!backendData) return <DemoComponent />` — demo fallback
- Inline state machine logic inside `main.jsx` beyond `useReducer` wiring
- Event type strings not validated against the typed event contract
- Command payloads built inline in UI event handlers (must go through `commands.js`)

---

## Implementation Boundaries

This is a documentation/policy story. No product code is created.

---

## Allowed Files

- `.tasks-md/Planning/S7-0005-Modular-frontend-architecture-and-design-extraction-policy.md` (this file)

---

## Forbidden Files

- No product code changes in this story
- No changes to `frontend_new_design_prototype/`
- No changes to `frontend/src/main.jsx`
- No changes to `frontend/src/aw-ide-panel.jsx`

---

## Acceptance Criteria

- [ ] `frontend_new_design_prototype/` is documented as visual reference only
- [ ] Module split boundaries are defined with location and responsibility
- [ ] Forbidden patterns are listed and specific
- [ ] Design token extraction protocol is actionable
- [ ] No monolith expansion rules are clear
- [ ] Policy is referenced by all Cluster 2–3 story files

---

## Evidence Required

- [ ] This file committed to `.tasks-md/Planning/`

---

## Stop Conditions

- A Cluster 2–3 story imports from `frontend_new_design_prototype/` — stop and remove the import
- A new module exceeds 300 lines without a documented split plan — file a story first
- A production component contains hardcoded demo data — stop and remove before merging
