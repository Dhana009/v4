# S6-0904 Replay one/all backend product flow

**Sprint:** Sprint 6  
**Cluster:** 9 (Replay Repair, Save/Load, Session Restore, Versioning)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Replay Engine  
**Blocks:** S6-0905  
**Blocked by:** S6-0903  

---

## Purpose

Complete backend replay for one step, one operation, and all recorded steps. Replay_step, replay_operation, replay_all, precondition checks, locator revalidation, operation execution through backend, replay_result event, and failure enters recovery/replay repair path. No frontend simulation, no direct recording mutation during replay, no LLM repair yet.

---

## What it contains

```
- replay_step
- replay_operation
- replay_all
- replay precondition checks
- locator revalidation
- operation execution through backend
- replay_result event
- failure enters recovery/replay repair path
```

---

## What it must NOT contain

```
- no frontend simulation
- no direct recording mutation during replay
- no LLM repair yet
```

---

## Tests first

Unit tests: replay_step loads parent step, replay_operation loads child, replay_all respects order, precondition mismatch blocks.

Contract tests: replay_result typed, failure emits recovery_needed or replay_repair_needed, no mutation by default.

Integration tests: save/load/replay one, save/load/replay all.

Coverage: **95%**

---

## Allowed files

```
runtime/replay_contracts.py (new)
tests/test_replay_contracts.py (new)
Minor edits to: agent.py, browser.py
```

---

## Sign-off

- [x] Story is specific (replay backend implementation)
- [x] Tests are first
- [x] Blocks S6-0905 (failure classification)
