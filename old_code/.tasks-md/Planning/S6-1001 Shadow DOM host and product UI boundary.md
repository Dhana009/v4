# S6-1001 Shadow DOM host and product UI boundary

**Sprint:** Sprint 6  
**Cluster:** 10 (Frontend Complete LLM Mode UI)  
**Tier:** 1 (core)  
**Type:** Feature / Architecture  
**Status:** Planning  
**Owner:** Frontend Architecture  
**Blocks:** S6-1002, S6-1003, S6-1004, S6-1005, S6-1006, S6-1007, S6-1008  
**Blocked by:** S6-0909  

---

## Purpose

Ensure frontend product UI is separated from host/mounting logic. Shadow DOM host mount lifecycle, product UI independent from overlay-only globals, backend websocket config passed through host adapter, stable root/test hooks, and unmount cleanup.

---

## What it contains

- Shadow DOM host mount lifecycle
- product UI independent from overlay-only globals
- backend websocket config passed through host adapter
- stable root/test hooks
- unmount cleanup

---

## What it must NOT contain

- no duplicate legacy overlay product logic
- no browser.py product UI logic
- no broad UI redesign

---

## Tests first

Unit/contract: product UI mounts in Shadow DOM, root has stable data-testid, unmount removes listeners, components don't depend on page CSS/globals.

Cheap E2E: panel visible in Shadow DOM, target page CSS doesn't break panel.

Coverage: **95%**

---

## Allowed files

```
frontend/src/host/ (new)
frontend/src/index.ts (updated)
frontend/src/test-utils/ (test hooks)
Tests: test_host_mount.ts
```

---

## Sign-off

- [x] Story is specific (Shadow DOM + product UI boundary)
- [x] Tests are first
- [x] Blocks all frontend tabs
