# S6-0908 Save repaired version and retain history

**Sprint:** Sprint 6  
**Cluster:** 9  
**Tier:** 1 (core)  
**Type:** Feature / Versioning  
**Status:** Planning  
**Owner:** Versioning  
**Blocks:** S6-0909  
**Blocked by:** S6-0907  

---

## Purpose

Support versioned save after replay repair. Version metadata, previous version reference, repair history, old locator/action/code retained, and new version save path.

---

## What it contains

- version metadata
- previous version reference
- repair history
- old locator/action/code retained
- new version save path

---

## Tests first

Unit: save new version increments version, old version retained, repair history links old/new operation, version metadata serializable.

Contract: repaired session save emits version_saved event, frontend can show previous/current version.

Integration: save v1 → replay repair → save v2 → load both metadata.

Coverage: **95%**

---

## Allowed files

```
runtime/versioning_contracts.py (new)
recording/versioning.py (new)
tests/test_versioning_contracts.py (new)
Minor edits: session_save_contracts.py
```

---

## Sign-off

- [x] Story is specific (version and history)
- [x] Tests are first
- [x] Blocks S6-0909 (integration proof)
