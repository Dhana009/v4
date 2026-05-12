# S6-1004 Steps tab: scoped step builder and locator state

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / UI Tab  
**Status:** Planning  
**Owner:** Frontend Steps Tab  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Complete scoped Steps workflow UI. Add/edit/delete/reorder/duplicate steps, attach/pick element/section, expected outcome/postcondition, test data reference, locator status, improve/revalidate/change scope actions, dependency warnings, run selected/all.

---

## What it contains

- add/edit/delete/reorder/duplicate steps
- attach/pick element or section
- expected outcome/postcondition
- test data reference
- locator status badges
- improve/revalidate/change scope actions
- dependency warnings
- run selected/all

---

## Tests first

Frontend tests: step_id remains identity when reordered, expected outcome shown as metadata, locator status badges render backend state, dependency_warning renders inline, improve locator sends typed command.

Coverage: **95%**

---

## Allowed files

```
frontend/src/components/steps/ (new)
frontend/src/store/steps.ts (new)
Tests: test_steps_tab.ts
```

---

## Sign-off

- [x] Story is specific (Steps tab UI)
- [x] Tests are first
- [x] Blocks integration proof
