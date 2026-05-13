# S7-0306 Frontend Module Structure Creation

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0306  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Create modular frontend architecture with clear boundaries: host, transport, store, commands, components. Prevent monolith growth.

---

## Scope vs S7-0502 (cross-reference)

- **S7-0306 owns module/folder structure and empty/minimal stubs only.**
- S7-0306 must **not** implement reducer/store behavior. Stubs may declare exported names and types only.
- S7-0306 must **not** duplicate S7-0502 implementation work.
- If imports break or build fails after stub creation, **stop and roll back** the module skeleton changes; do not patch logic into stubs to compensate.
- S7-0502 fills/replaces the `frontend/src/store/` stubs created here with the real reducer, selectors, and event-store implementation.

---

## Module Structure (Target)

```
frontend/src/
├── host/                    # Shadow DOM host
│   ├── host.jsx
│   ├── host-styles.jsx
│   └── __tests__/
├── transport/               # WebSocket/events
│   ├── websocket-client.js
│   ├── event-receiver.js
│   ├── command-sender.js
│   └── __tests__/
├── store/                   # State reducer
│   ├── reducer.js
│   ├── selectors.js
│   ├── types.js
│   └── __tests__/
├── commands/                # Command builders
│   ├── command-builder.js
│   ├── validation.js
│   └── __tests__/
├── components/              # UI components
│   ├── shell/
│   ├── llm/
│   ├── steps/
│   ├── manual/
│   ├── recorded/
│   ├── code/
│   ├── trace/
│   ├── agents/
│   └── primitives/
├── styles/
│   ├── tokens.css
│   ├── globals.css
│   └── components.css
└── test-utils/
    └── render.js
```

---

## Tests First

### Module Tests

**Test: No circular imports**
- Run circular dependency detector.
- Report: any circular imports found.

**Test: Module boundaries**
- Verify host/ imports only from transport, store.
- Verify transport/ imports only from types.
- Verify commands/ imports only from types.
- Verify components/ import from commands, store, transport.

**Test: No backend in frontend**
- Verify no imports from `runtime/`, `agent`, `server`, `browser` modules.
- Grep confirms all imports are local to frontend/.

---

## Implementation Boundaries

### Allowed Changes

- **Create module files:**
  - `frontend/src/host/host.jsx`
  - `frontend/src/transport/websocket-client.js`
  - `frontend/src/store/reducer.js`
  - `frontend/src/store/types.js`
  - `frontend/src/store/selectors.js`
  - `frontend/src/commands/command-builder.js`
  - `frontend/src/commands/validation.js`
  - `frontend/src/test-utils/render.js`

- **Update main.jsx** to import from modules.

- **Create tests:** `tests/test_frontend_imports.py`

### Forbidden Changes

- No implementation logic (Cluster 5+).
- No state wiring (Cluster 5+).

---

## Acceptance Criteria

✅ **Module files created** — All folders and stubs in place.
✅ **No circular imports** — Module structure verified clean.
✅ **No backend imports** — Only local frontend imports.
✅ **Build succeeds** — `npm run build`.
✅ **Evidence:** module list, circular dependency check, build output.

---

## Evidence Checklist

- [ ] Module folders and stub files created
- [ ] Circular import check run and passed
- [ ] No backend imports detected
- [ ] Build succeeds: `npm run build`
- [ ] Tests pass: `tests/test_frontend_imports.py`
- [ ] Story updated with evidence

