# S6-1006 Recorded tab: immutable evidence and repair/version display

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / UI Tab  
**Status:** Planning  
**Owner:** Frontend Recorded Tab  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Show what actually happened. Recorded parent steps, child operations, locator used, observed result, expected/observed outcome, code snippets, replay status, repair status, version history.

---

## What it contains

- recorded parent steps
- child operations
- locator used
- observed result
- expected/observed outcome
- code snippets
- replay status
- repair status
- version history display

---

## Tests first

Frontend tests: step_recorded adds recorded evidence, child operation status shown, repaired operation shows old/new version metadata, unresolved failed step not shown as recorded.

Coverage: **95%**

---

## Allowed files

```
frontend/src/components/recorded/ (new)
frontend/src/store/recorded.ts (new)
Tests: test_recorded_tab.ts
```

---

## Sign-off

- [x] Story is specific (Recorded tab)
- [x] Tests are first
