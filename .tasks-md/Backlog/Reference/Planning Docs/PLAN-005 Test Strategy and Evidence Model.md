# PLAN-005 Test Strategy and Evidence Model

**Type:** Planning Control  
**Status:** Planning  
**Priority:** P0  
**Owner:** Planning Brain  
**Applies To:** All implementation stories  

---

## 1. Purpose

Testing is part of each story, not a later QA phase.

This product combines LLM reasoning, backend validation, frontend rendering, and browser automation. Therefore every story needs tests designed before coding.

---

## 2. Test layers

| Layer | Used for | Examples |
|---|---|---|
| Unit | Local logic | state reducer, schema validator, skill policy |
| Integration | Subsystems | command → state, plan → execution contract |
| Contract | Payloads/schemas | events, commands, LLM outputs |
| Frontend | UI state rendering | Shadow DOM rendering from typed events |
| E2E/harness | Full product behavior | intent → plan → confirm → execute → record |
| Regression | Known failures | correction order, exact text assertion, replay smoke |

---

## 3. Real-world fixtures

Required fixture classes:

- Playwright docs-style page
- weak WordPress/Elementor-style page
- lead-magnet-style form page
- modal/dropdown page
- card/table/dashboard page
- code-block/assertion page

Each fixture should expose known locator challenges:

- duplicate CTA
- weak div/span button
- scoped section assertion
- code block exact text
- modal dialog
- dropdown
- dynamic page state

---

## 4. Evidence required per story

Every story in `Review` must provide:

```text
files inspected
files changed
tests added
commands run
command output
sample payloads/events
screenshots/traces if UI/E2E
architecture drift check
remaining risks
```

---

## 5. Test matrix format

Every story should use:

| Test ID | Layer | Scenario | Input/Setup | Expected result | Source rule protected |
|---|---|---|---|---|---|

---

## 6. Regression flows before P0 acceptance

P0 regression must cover:

1. Basic click
2. Basic visible assertion
3. Exact text/code block assertion
4. Correction: assert then click
5. Multi-step isolation
6. Clarification path
7. Recovery path
8. Recording parent/child output
9. Code update
10. Replay smoke
11. Shadow DOM UI state rendering
12. Trace evidence path

---

## 7. Acceptance rule

A story cannot move to Done unless:

- tests exist
- tests pass
- evidence is complete
- no source conflict remains
- no architecture rule is violated
- skipped/unsupported behavior is explicitly tracked
