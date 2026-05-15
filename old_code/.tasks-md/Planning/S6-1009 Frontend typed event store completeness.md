# S6-1009 Frontend typed event store completeness

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / State Management  
**Status:** Planning  
**Owner:** Frontend State Store  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Ensure every Complete LLM Mode event maps to UI state. Conversation_state, clarification_needed, permission_required, page_analysis_started, recommendation_ready, plan_ready, plan_diff_proposed/validated/applied, dependency_warning, locator_ambiguous, precondition_failed, execution_started, recovery_needed, step_recorded, code_update, replay_started/result, session_state, runtime_rejected.

---

## What it contains

- conversation_state
- clarification_needed
- permission_required
- page_analysis_started
- recommendation_ready
- plan_ready
- plan_diff_proposed/validated/applied
- dependency_warning
- locator_ambiguous
- precondition_failed
- execution_started
- recovery_needed
- step_recorded
- code_update
- replay_started/result
- session_state
- runtime_rejected

---

## Tests first

Contract tests: each event updates only allowed UI slice, unknown event logs visible developer diagnostic, stale run event rejected/ignored with warning.

Coverage: **95%**

---

## Allowed files

```
frontend/src/store/ (extend existing)
frontend/src/events/ (new)
Tests: test_event_store.ts
```

---

## Sign-off

- [x] Story is specific (event store)
- [x] Tests are first
