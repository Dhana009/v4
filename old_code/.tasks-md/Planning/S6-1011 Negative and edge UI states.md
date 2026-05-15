# S6-1011 Negative and edge UI states

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / UI Error States  
**Status:** Planning  
**Owner:** Frontend Error States  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Complete UI for common failures. Backend down, API key missing/invalid, browser launch failed, LLM provider timeout, schema failure retry/fail, websocket disconnect/reconnect, long-running wait, recorded succeeded but code failed, unsupported capability.

---

## What it contains

- backend down state + retry/trace
- API key missing/invalid state
- browser launch failed state
- LLM provider timeout state
- schema failure retry/fail state
- websocket disconnect/reconnect state
- long-running operation wait UI
- recorded succeeded but code failed state
- unsupported capability state + safe actions

---

## Tests first

Frontend tests: backend down shows retry/trace, schema failure shows retrying then failed state, websocket disconnect doesn't show success, codegen failure after recording is visible, unsupported capability shows limitation and safe actions.

Coverage: **95%**

---

## Allowed files

```
frontend/src/components/error-states/ (new)
frontend/src/store/error.ts (new)
Tests: test_error_states.ts
```

---

## Sign-off

- [x] Story is specific (negative/edge states)
- [x] Tests are first
