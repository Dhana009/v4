# S7-0301 Current Frontend Architecture Audit

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0301  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Audit the current frontend (production and prototype) to document structure, entry points, static vs. live paths, and monolith risks before implementing Cluster 3 refactoring.

---

## Audit Scope

- **Entry point** — `frontend/src/main.jsx` structure
- **Shadow DOM host** — Setup and lifecycle
- **Transport** — WebSocket connection, event receiver
- **State** — Local state vs. backend events
- **IDEPanel** — Props threading, lifecycle
- **Static files** — Demo content, fallbacks
- **Build** — Current build command, output structure
- **Test setup** — Existing test infrastructure
- **Monolith risks** — Files exceeding 200 lines
- **Prototype** — Structure of reference design

---

## Tests First

### Audit Tests (no implementation required; evidence report needed)

**Test: Entry point and host setup**
- Verify `frontend/src/main.jsx` exists.
- Verify Shadow DOM host ID and mounting strategy.
- Verify transport hook setup.
- Report: entry point structure, host mounting code snippet.

**Test: Transport and event receiver**
- Verify WebSocket connection setup.
- Verify event receiver pattern.
- Report: event receiver code, subscription pattern.

**Test: IDEPanel props**
- Verify what props IDEPanel currently receives.
- Verify what state is passed.
- Report: current prop shape, state threading.

**Test: Static vs. live paths**
- Grep for demo content, mock data.
- Identify which components render static data.
- Report: list of static/demo files.

**Test: Build system**
- Verify `npm run build` works.
- Verify output structure.
- Report: build output, bundle size.

**Test: Test infrastructure**
- Verify test setup (Jest, Vitest, or other).
- Report: test framework, test file locations.

**Test: Monolith files**
- Find all .jsx files > 200 lines.
- Report: files needing split, line counts.

**Test: Prototype structure**
- List files in `frontend_new_design_prototype/`.
- Report: structure, component names, potential reuse.

---

## Implementation Boundaries

**Audit only; no code changes.** Produce evidence report.

---

## Acceptance Criteria

✅ **Audit report created** with sections:
- Entry point and Shadow DOM setup
- Transport/event receiver pattern
- IDEPanel props and state threading
- Static vs. live component list
- Build command and output structure
- Test framework and locations
- Monolith files (>200 lines) with line counts
- Prototype structure and reusable patterns
- Risk summary (monoliths, static content, circular imports)

✅ **Report stored** as `.tasks-md/Planning/S7-0301-AUDIT-REPORT.md`

---

## Evidence Checklist

- [ ] Audit report created with all sections
- [ ] Line counts verified for monolith files
- [ ] Static content locations identified
- [ ] Build verified to work
- [ ] Prototype structure documented
- [ ] Evidence submitted with story Done

