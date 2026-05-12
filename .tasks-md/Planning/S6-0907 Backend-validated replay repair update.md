# S6-0907 Backend-validated replay repair update

**Sprint:** Sprint 6  
**Cluster:** 9  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Repair Validation  
**Blocks:** S6-0908  
**Blocked by:** S6-0906  

---

## Purpose

Apply validated replay repair to recording/code only after proof. Repair diff validation, live validation of repaired locator/action/assertion, update only affected child operation, new code_update after validated repair, and repair metadata on recorded step.

---

## What it contains

- repair diff validation
- live validation of repaired locator/action/assertion
- update only affected child operation
- new code_update after validated repair
- repair metadata on recorded step

---

## Tests first

Unit: repaired locator validates before activation, old locator retained, only failed operation updated, unresolved repair cannot emit code_update.

Contract: step_recorded/code_update ordering preserved, repair_applied event includes old/new diff.

Integration: replay failure → repair diff → validation → updated recorded operation → code_update.

Coverage: **95%**

---

## Allowed files

```
Minor edits: recording/replay.py, recording/codegen.py
Tests: test_replay_repair_validation.py
```

---

## Sign-off

- [x] Story is specific (validate and apply repair)
- [x] Tests are first
- [x] Blocks S6-0908 (versioning)
