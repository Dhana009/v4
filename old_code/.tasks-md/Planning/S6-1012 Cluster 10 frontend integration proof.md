# S6-1012 Cluster 10 frontend integration proof

**Sprint:** Sprint 6  
**Cluster:** 10 (Frontend Complete LLM Mode UI)  
**Tier:** 2 (integration proof)  
**Type:** Integration / E2E  
**Status:** Planning  
**Owner:** Frontend Integration  
**Blocks:** (Cluster 10 release gate)  
**Blocked by:** S6-1003, S6-1004, S6-1005, S6-1006, S6-1007, S6-1008, S6-1009, S6-1010, S6-1011  

---

## Purpose

Prove major frontend Complete LLM Mode states with cheap local E2E/component tests. Fixture-based integration tests, no paid LLM/E2E, all tabs complete and functional.

---

## Required flows

```
1. session_state → global header + recorded/code state
2. page recommendation → recommendation card → accept subset
3. plan_ready → confirm/correction
4. recovery_needed → recovery card
5. locator_ambiguous → candidate choice
6. replay_result → Recorded tab status
7. runtime_rejected → error state
8. websocket disconnect/reconnect
```

---

## What it contains

- fixture-based integration tests
- no paid LLM/E2E
- all tabs complete
- all flows end-to-end

---

## Tests first

Integration/cheap E2E tests: frontend renders backend event stream, commands are typed and complete, no lifecycle inference, Shadow DOM selectors work, critical actions keyboard-accessible.

Regression tests: existing frontend event/command contract tests, Shadow DOM contract tests, E2E harness selector tests.

Coverage: **95%**

---

## Allowed files

```
tests/test_cluster10_frontend_e2e.ts (new)
tests/fixtures/cluster10_e2e_scenarios.ts (new)
```

---

## Sign-off

- [x] Story is specific (prove Cluster 10 frontend)
- [x] Tests are first (scenario-based)
- [x] Releases Cluster 10 gate + Sprint 6 complete
