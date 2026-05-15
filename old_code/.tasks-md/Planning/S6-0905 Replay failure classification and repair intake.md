# S6-0905 Replay failure classification and repair intake

**Sprint:** Sprint 6  
**Cluster:** 9  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Failure Classification  
**Blocks:** S6-0906  
**Blocked by:** S6-0904  

---

## Purpose

Classify replay failure and prepare repair context. Replay failure classification, old locator/action evidence, current page evidence, stored locator context, replay repair packet, and bounded context.

---

## What it contains

- replay failure classification
- old locator/action evidence
- current page evidence
- stored locator context
- replay repair packet
- bounded context

---

## What it must NOT contain

- no full raw DOM by default
- no direct LLM mutation
- no saved version yet

---

## Tests first

Unit: broken locator → replay_locator_failed, assertion mismatch → replay_assertion_failed, wrong page → replay_precondition_failed, unsupported → capability_gap.

Contract: repair packet includes recorded operation + failure evidence, excludes secrets/raw DOM.

Coverage: **95%**

---

## Allowed files

```
runtime/replay_failure_classifier.py (new)
runtime/replay_repair_packet.py (new)
tests/test_replay_failure_classifier.py (new)
```

---

## Sign-off

- [x] Story is specific (classify replay failure)
- [x] Tests are first
- [x] Blocks S6-0906 (repair policy)
