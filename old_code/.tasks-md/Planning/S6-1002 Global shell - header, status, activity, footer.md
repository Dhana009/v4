# S6-1002 Global shell: header, status, activity, footer

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / UI  
**Status:** Planning  
**Owner:** Frontend Shell  
**Blocks:** S6-1003, S6-1004, S6-1005, S6-1006, S6-1007, S6-1008  
**Blocked by:** S6-1001  

---

## Purpose

Build the global UI shell. Connection status, backend phase, current URL, active run/session, active plan/version, blocking state, compact activity strip, common actions.

---

## What it contains

- connection status
- backend phase
- current URL
- active run/session
- active plan/version
- blocking state
- compact activity strip
- common actions

---

## Tests first

Frontend unit/contract: status renders from backend events, phase changes only through typed event, blocking state visible, disconnected state visible.

Integration: session_state updates header, runtime_rejected shows compact error.

Coverage: **95%**

---

## Allowed files

```
frontend/src/components/shell/ (new)
frontend/src/store/shell.ts (new)
Tests: test_shell.ts
```

---

## Sign-off

- [x] Story is specific (global shell)
- [x] Tests are first
- [x] Blocks all tab components
