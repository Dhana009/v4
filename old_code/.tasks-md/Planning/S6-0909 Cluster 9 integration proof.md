# S6-0909 Cluster 9 integration proof

**Sprint:** Sprint 6  
**Cluster:** 9  
**Tier:** 2 (integration proof)  
**Type:** Integration / E2E  
**Status:** Planning  
**Owner:** Integration  
**Blocks:** (Cluster 9 release gate)  
**Blocked by:** S6-0908  

---

## Purpose

Prove the full replay/save/repair/version loop locally. Fixture-based integration tests, fake LLM planner, no paid LLM, no execution until confirmation.

---

## Required flows

```
1. record/save/load/replay one
2. replay all with ordered results
3. broken locator replay → repair → code_update
4. repaired session saved as new version
5. malformed load rejected safely
```

---

## What it contains

- fixture-based integration tests
- fake LLM planner
- no paid LLM
- no execution until confirmation

---

## Tests first

Integration/cheap E2E: no frontend simulation, backend emits replay_started/replay_result, repair does not mutate before validation, version history retained, artifacts include replay/repair payloads.

Regression: recording/code_update truth, backend event contract, locator context, recovery lifecycle.

Coverage: **95%**

---

## Allowed files

```
tests/test_cluster9_cheap_e2e.py (new)
tests/fixtures/cluster9_e2e_scenarios.py (new)
```

---

## Sign-off

- [x] Story is specific (prove Cluster 9)
- [x] Tests are first (scenario-based)
- [x] Releases Cluster 9 gate
