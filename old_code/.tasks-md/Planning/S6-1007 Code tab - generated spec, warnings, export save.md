# S6-1007 Code tab: generated spec, warnings, export/save

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / UI Tab  
**Status:** Planning  
**Owner:** Frontend Code Tab  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Complete code review/export experience. Full generated spec preview, latest code_update, source recorded step mapping, fragile locator warnings, unsupported capability skipped warnings, copy/export/save actions.

---

## What it contains

- full generated spec preview
- latest code_update
- source recorded step mapping
- fragile locator warnings
- unsupported capability skipped warnings
- copy/export/save actions

---

## Tests first

Frontend tests: code_update renders lines/full preview, fragile locator warning visible, codegen failure state visible, save/export sends backend command.

Coverage: **95%**

---

## Allowed files

```
frontend/src/components/code/ (new)
frontend/src/store/code.ts (new)
Tests: test_code_tab.ts
```

---

## Sign-off

- [x] Story is specific (Code tab)
- [x] Tests are first
