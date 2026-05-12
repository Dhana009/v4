# S6-1008 Trace tab: event timeline and diagnostics

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / UI Tab  
**Status:** Planning  
**Owner:** Frontend Trace Tab  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Make Trace tab the observability workspace. Event timeline, LLM calls/token estimates, context policy used, locator decisions, permission decisions, precondition checks, failures/recoveries, artifact links, filters, failure detail view.

---

## What it contains

- event timeline
- LLM calls/token estimates
- context policy used
- locator decisions
- permission decisions
- precondition checks
- failures/recoveries
- artifact links
- filters
- failure detail view

---

## Tests first

Frontend tests: trace rows render by type, filters don't change runtime state, failure detail shows expected/actual/evidence/next actions, redacted payload remains redacted.

Coverage: **95%**

---

## Allowed files

```
frontend/src/components/trace/ (new)
frontend/src/store/trace.ts (new)
Tests: test_trace_tab.ts
```

---

## Sign-off

- [x] Story is specific (Trace tab)
- [x] Tests are first
