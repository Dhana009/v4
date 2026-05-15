# S6-0906 replay_repair_specialist controller path

**Sprint:** Sprint 6  
**Cluster:** 9  
**Tier:** 1 (core)  
**Type:** Feature / Policy  
**Status:** Planning  
**Owner:** Repair Policy  
**Blocks:** S6-0907  
**Blocked by:** S6-0905  

---

## Purpose

Wire replay repair through controller as its own LLM purpose. Replay_repair_specialist purpose use, compact repair packet, repair diff output, backend validation, and bounded retry/fallback.

---

## What it contains

- replay_repair_specialist purpose use
- compact repair packet
- repair diff output
- backend validation
- bounded retry/fallback

---

## Tests first

Unit: policy resolves, output is diff, invalid schema retries once then fails closed, LLM cannot emit step_recorded/code_update.

Contract: repair diff targets recorded step/operation, locator repair validates count==1, assertion repair preserves intent.

Coverage: **95%**

---

## Allowed files

```
runtime/replay_repair_flow.py (new)
tests/test_replay_repair_flow.py (new)
Minor edits: llm_runtime_controller.py, llm_policy_registry.py
```

---

## Sign-off

- [x] Story is specific (wire repair policy)
- [x] Tests are first
- [x] Blocks S6-0907 (validation + update)
