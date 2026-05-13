# S7-0304 Component Inventory and Production Mapping

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0304  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Define production component inventory (AppShell, Header, Tabs, Cards, Steps, Manual, Recorded, Code, Trace, Agent components) and map each to module/test location. No implementation; planning and structure only.

---

## Component Inventory (Target)

### Shell Components
- **AppShell** — Main layout container
- **Header** — Top bar with title, mode selector
- **TabBar** — Tab selector (LLM, Steps, Recorded, Code, Trace)
- **DockController** — Resize, collapse, position

### LLM Tab Components
- **PlanCard** — Show plan with accept/reject
- **ClarificationCard** — Show question, input response
- **RecommendationCard** — Show suggestions, accept/reject
- **CorrectionCard** — Show plan diff, apply/reject
- **PermissionCard** — Show permission request, approve
- **LocatorAmbiguityCard** — Show candidates, select
- **RecoveryCard** — Show options, select action
- **ExecutionCard** — Show step status
- **CompletedCard** — Show final summary

### Steps Tab Components
- **StepsPanel** — List of steps with actions
- **StepBuilder** — Add/edit/delete step UI
- **ManualActionBuilder** — Build custom action (Phase 4)
- **ManualAssertionBuilder** — Build custom assertion (Phase 4)
- **ElementPicker** — Select element on page
- **LocatorCandidateList** — Show/select from candidates

### Recorded/Code/Trace/Agent Components
- **RecordedPanel** — Show recorded evidence
- **CodePanel** — Show generated Playwright code
- **CodeLinker** — Map code lines to recorded steps
- **TracePanel** — Show timeline, filters
- **AgentActivityView** — Show agent messages (compact)

### Shared Primitives
- **Button** — Primary, secondary, danger variants
- **Card** — Container with optional header/footer
- **Badge** — Status pills
- **StatusPill** — Small status indicator
- **EmptyState** — No data message
- **InlineAlert** — Error/warning message
- **ActionRow** — Horizontal button layout
- **CodeBlock** — Code display with syntax highlight
- **TimelineRow** — Single event in timeline
- **CandidateCard** — Locator candidate preview

---

## Tests First

### Structure Tests

**Test: Component folder structure**
- Verify folders exist: `components/shell/`, `components/llm/`, etc.
- Report: folder structure with expected component files.

**Test: Component naming**
- Verify component names match inventory.
- Verify .jsx files match component names.

**Test: No circular imports**
- Grep for circular import patterns.
- Report: any circular dependencies found.

### Integration Tests

**Test: Import structure**
- Verify components can be imported from their modules.
- Verify no import errors.

---

## Implementation Boundaries

### Allowed Changes

- **Create folders:**
  - `frontend/src/components/shell/`
  - `frontend/src/components/llm/`
  - `frontend/src/components/steps/`
  - `frontend/src/components/manual/`
  - `frontend/src/components/recorded/`
  - `frontend/src/components/code/`
  - `frontend/src/components/trace/`
  - `frontend/src/components/agents/`
  - `frontend/src/components/primitives/`

- **Create stub component files** (no implementation)
  - Each component as empty JSX function or export.
  - For now: `export default function ComponentName() { return null; }`

- **Create test structure:**
  - `frontend/src/components/*/ComponentName.test.jsx` for each component.
  - Tests can be minimal (check render without crash).

- **Update import maps/index files** if using barrel exports.

### Forbidden Changes

- No component logic implementation (Cluster 5+).
- No state threading (Cluster 5+).
- No backend event binding (Cluster 5+).

---

## Acceptance Criteria

✅ **Folder structure complete** — All component folders created.
✅ **Stub files created** — Each component has empty .jsx file.
✅ **No circular imports** — Module structure is clean.
✅ **Build succeeds** — `npm run build` with stubs.
✅ **Evidence:** folder listing, build output, test results.

---

## Evidence Checklist

- [ ] Component folders created
- [ ] Stub .jsx files created for all components
- [ ] No circular imports detected
- [ ] Build succeeds: `npm run build`
- [ ] Test stubs created (can be minimal)
- [ ] Story updated with evidence

