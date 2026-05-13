# Sprint 7 — Cluster 3: Frontend Architecture & Design Extraction

**Sprint:** Sprint 7  
**Cluster:** 3  
**Status:** Planning  
**Date:** 2026-05-13  
**HEAD at planning:** 8bdd8de  

---

## Cluster 3 Goal

Convert `frontend_new_design_prototype` into production frontend architecture and component structure. This cluster does **not** implement UI (that's Cluster 6–9). It does **not** wire live transport (Cluster 5). It plans modular boundaries, extracts design patterns, and creates reusable primitives. After Cluster 3, the frontend is architecturally ready for component implementation.

---

## Current Frontend State

### Current Production Frontend

- `frontend/src/main.jsx` — Entry point, Shadow DOM host setup, state transport hook.
- `frontend/src/aw-ide-panel.jsx` — Main panel component (large, static/demo content).
- `frontend/src/aw-tabs.jsx`, `aw-bits.jsx`, other JSX files — Static demo components.
- `frontend/` — Shadow DOM mount, transport wiring exist; state not fully threaded into UI.
- Build: `npm run build` compiles to frontend/dist.
- Current issue: live transport/state exists but UI is static/demo; modular structure missing.

### `frontend_new_design_prototype`

- `llm-tab.jsx`, `secondary-tabs.jsx`, `chrome.jsx`, `app.jsx`, etc. — Design-only reference.
- **Role:** Visual reference and component structure inspiration, not runtime state.
- **Do not:** Copy static demo state into production as runtime truth.
- **Do:** Extract visual tokens, component patterns, tab layout structure.

---

## Frontend Architecture Design

### High-level structure (target)

```
frontend/src/
├── host/                    # Shadow DOM host and lifecycle
│   ├── host.jsx
│   └── host-styles.jsx
├── transport/               # WebSocket and backend events
│   ├── websocket-client.js
│   ├── event-receiver.js
│   └── command-sender.js
├── store/                   # Frontend state reducer
│   ├── reducer.js
│   ├── selectors.js
│   └── types.js
├── commands/                # Frontend command builders
│   ├── command-builder.js
│   └── validation.js
├── components/
│   ├── shell/               # Main app structure
│   │   ├── AppShell.jsx
│   │   ├── Header.jsx
│   │   └── TabBar.jsx
│   ├── llm/                 # LLM tab cards
│   │   ├── PlanCard.jsx
│   │   ├── ClarificationCard.jsx
│   │   ├── RecommendationCard.jsx
│   │   └── ...
│   ├── steps/               # Steps tab
│   │   ├── StepsPanel.jsx
│   │   └── StepBuilder.jsx
│   ├── manual/              # Manual mode (Phase 4, limited)
│   ├── recorded/            # Recorded evidence
│   ├── code/                # Code display
│   ├── trace/               # Trace/debug
│   ├── agents/              # Agent visibility
│   └── primitives/          # Shared UI elements
│       ├── Button.jsx
│       ├── Card.jsx
│       ├── Badge.jsx
│       └── ...
├── styles/
│   ├── tokens.css           # Design tokens
│   ├── globals.css
│   └── components.css
└── test-utils/
    └── render.js            # Component test helpers
```

---

## Source Rules (Priority Order)

1. **Frontend UI Spec** — `autoworkbench_complete_llm_mode_frontend_ui_spec.md`
2. **PRD v2.3** — `03_FRONTEND_RUNTIME.md`, `04_BACKEND_EVENT_CONTRACT.md`
3. **Cluster 2 Event Contracts** — `.tasks-md/Sprints/SPRINT-007-CLUSTER-2-*.md` (event payload shapes)
4. **Sprint 7 Governance** — Architecture rules and modularization
5. **design_prototype** — Visual reference only; do not copy state

---

## Design to Production Conversion Rules

1. **Design is reference, not source of truth** — Components can be inspired by prototype but must render backend events, not static demo data.
2. **No lifecycle inference** — If a component needs to be hidden/shown based on lifecycle, that info must come from backend event state, not CSS state or prop assumptions.
3. **Empty states are explicit** — "No data yet" is better than default demo content.
4. **Interaction is typed commands** — Frontend buttons emit typed command objects to backend, not string messages.
5. **Visual tokens extracted, not copied** — Colors, spacing, fonts are extracted to token file, not hard-coded in components.

---

## Story List

### Cluster 3 Stories (8 total)

1. **S7-0301** — Current frontend architecture audit
2. **S7-0302** — frontend_new_design_prototype extraction map
3. **S7-0303** — Design token extraction and style system
4. **S7-0304** — Component inventory and production mapping
5. **S7-0305** — Static demo fallback removal strategy
6. **S7-0306** — Frontend module structure creation
7. **S7-0307** — Shared UI primitives production baseline
8. **S7-0308** — Frontend data-testid and accessibility baseline

---

## Implementation Scope

### Allowed Files

- `frontend/src/**` — All frontend implementation
- `frontend_new_design_prototype/**` — Read-only reference (no modifications during Cluster 3)
- `frontend/styles/**` — Style system and tokens
- `frontend/package.json` — Dependency updates only if justified
- `frontend/build/**` — Build config updates only if justified
- `tests/test_frontend*.py` — Frontend build/import tests
- `tests/frontend/**` — Component test files if existing

### Forbidden Files

- `runtime/**` — No backend/LLM implementation during Cluster 3
- `browser.py` — No browser automation
- `agent.py` — No backend logic
- `frontend_new_design_prototype/**` — Do not modify; read-only reference
- `.DS_Store`, `AGENTS.md` — Do not stage local noise
- Backend or test files with product code

---

## Architecture Rules (Cluster 3 specific)

1. **Modular boundaries clear** — Each UI domain (shell, llm, steps, etc.) has focused folder and tests.
2. **No static demo as runtime truth** — Design prototype shows what UI could look like; actual components render backend events.
3. **Component receives props as backend events** — `<PlanCard plan={planEvent} onReview={handler} />`, not `<PlanCard demoData={staticPlan} />`.
4. **Shared primitives used widely** — Button, Card, Badge reused; no copy-paste UI.
5. **Design tokens centralized** — Colors, spacing, fonts in `tokens.css`; no hard-coded values in components.
6. **No lifecycle inference** — Hidden/shown state comes from event props, not component logic guessing.
7. **Accessibility built-in** — All interactive controls have stable data-testid, ARIA labels, keyboard support.

---

## Tests-First Requirements

### Test Taxonomy for Cluster 3

| Test type | Purpose | Where | Required per story |
|---|---|---|---|
| **Module structure** | No circular dependencies, imports work | `tests/test_frontend_structure.py` | S7-0306 |
| **Component render** | Component renders with props | frontend component test files | S7-0307, S7-0304 |
| **Style system** | Tokens import, CSS compiles, Shadow DOM isolation | `tests/test_frontend_styles.py` | S7-0303 |
| **Build** | `npm run build` succeeds | `tests/test_frontend_build.py` | All stories |
| **No static demo truth** | Production mode does not render demo content | `tests/test_frontend_live_state.py` | S7-0305 |
| **Accessibility** | data-testid present, ARIA labels correct | `tests/test_frontend_a11y.py` | S7-0308 |
| **Import structure** | Component imports follow module boundaries | `tests/test_frontend_imports.py` | S7-0306 |

### Negative Tests Required

- Components without data-testid fail check.
- Static demo content in production code fails check.
- Circular imports detected and reported.
- Missing ARIA labels on buttons/links detected.

---

## Local-Only Validation Policy

Cluster 3 does **not** run:
- Browser E2E (Cluster 4 only).
- Backend integration (Cluster 5 wires transport).
- Paid LLM.
- Live websites.

Cluster 3 **does** run:
- Build tests: `npm run build` succeeds.
- Module structure tests.
- Component render tests (with mock props).
- Accessibility/testid checks.
- No static demo truth checks.

---

## Definition of Done

A Cluster 3 story is **Done** when:

1. ✅ All tests from `Tests First` section exist and are green.
2. ✅ Frontend file/folder structure matches plan.
3. ✅ No static demo content in production code.
4. ✅ Design tokens extracted and tokens.css complete.
5. ✅ Shared primitives defined with tests.
6. ✅ Modular boundaries maintained.
7. ✅ Build succeeds: `npm run build`.
8. ✅ Story file updated with evidence.

---

## Evidence Required

Before moving story to **Done**:

1. **Build evidence** — output of `npm run build` ✅
2. **Test evidence** — test file names and green output.
3. **Structure evidence** — folder layout matches plan.
4. **No demo truth** — grep shows no static demo rendering in live code.
5. **Accessibility evidence** — data-testid and ARIA labels present.

---

## Stop Conditions

**Stop and investigate if:**

1. **Build fails** — `npm run build` does not succeed.
2. **Circular imports detected** — Module structure violated.
3. **Demo state in production** — Static content being rendered as runtime truth.
4. **Missing tokens** — Design system incomplete.
5. **No tests** — Story skips test-first requirement.
6. **Monolith grows** — Component file exceeds 200 lines without planned split.

---

## Acceptance Criteria

After all Cluster 3 stories are **Done**:

1. **Frontend structure ready** — Modular folders and files in place.
2. **Design extracted** — Tokens, patterns, components mapped.
3. **No demo content** — Production code renders only from backend events.
4. **Shared primitives ready** — Button, Card, Badge, etc. defined and tested.
5. **Build succeeds** — `npm run build` green.
6. **Accessibility ready** — data-testid and ARIA labels in place.
7. **Tests passing** — Module, structure, style, a11y tests green.

---

## Known Risks

1. **Design prototype scope creep** — Easy to over-copy static UI; must discipline to backend-event-driven only.
2. **Component lifecycle inference** — Components might infer state instead of waiting for backend events.
3. **Build complexity** — CSS-in-JS, bundling, or import issues may delay.
4. **Component size** — Large components can exceed 200-line boundary; requires planned splits.

---

## Next Planning Task

After Cluster 3 is **Done**:
→ Create **Cluster 4 + Cluster 5 planning tickets** (frontend wiring and state management)

