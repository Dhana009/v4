# S6-1010 Frontend command dispatcher completeness

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / Commands  
**Status:** Planning  
**Owner:** Frontend Commands  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Ensure every UI action sends a typed backend command. Run/stop, answer clarification, permission decision, accept/remove/reorder recommendations, confirm plan, send correction, apply/reject diff, run selected/all steps, improve/revalidate locator, replay step/all, save/load, export/copy.

---

## What it contains

- run / stop commands
- clarification answer
- permission decision
- accept/remove/reorder recommendations
- confirm plan
- send correction
- apply/reject diff
- run selected/all steps
- improve/revalidate locator
- replay step/all
- save/load
- export/copy where backend-owned

---

## Tests first

Frontend contract tests: each button dispatches typed command, command includes run_id/plan_id/step_id where required, stale/missing IDs block dispatch or show error, duplicate confirm disabled or safely ignored.

Coverage: **95%**

---

## Allowed files

```
frontend/src/commands/ (new)
frontend/src/store/commands.ts (new)
Tests: test_command_dispatcher.ts
```

---

## Sign-off

- [x] Story is specific (command dispatcher)
- [x] Tests are first
