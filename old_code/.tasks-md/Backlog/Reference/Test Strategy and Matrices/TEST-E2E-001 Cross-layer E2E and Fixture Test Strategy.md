# TEST-E2E-001 Cross-layer E2E and Fixture Test Strategy

**Type:** Test Strategy  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-4 E2E Harness + Fixtures + Evidence  

## 1. Purpose

E2E proves the full system works together.

Required causal chains:
```text
frontend command → backend validation → backend event → frontend render
LLM output → schema validation → backend validator → plan_ready or rejection
DOM candidate → locator specialist → main LLM plan → backend/browser validation → execution or recovery
execution evidence → recording → code_update → frontend panel → artifact
failure → recovery → user choice → retry/skip/stop → terminal state
```

## 2. Required MVP flows

```text
MVP-001 lifecycle smoke
MVP-002 simple click
MVP-003 visible assertion
MVP-004 exact text/code assertion
MVP-005 correction before confirmation
MVP-006 clarification before planning
MVP-007 locator ambiguity/recovery
MVP-008 multi-step strict cursor
MVP-009 conditional save/load or typed gap
MVP-010 final acceptance gate
```

## 3. Fixture classes

```text
clean semantic page
weak div/span marketing page
docs/code-block page
form-heavy page
cards/table rows
modal/dialog page
portal dropdown page
toast/loading/spinner page
hidden mobile/desktop duplicate page
unsupported iframe/popup/upload/permission/download page
```

## 4. Positive E2E cases

```text
user prompt → plan_ready → UI plan → confirm → execution → recording → code_update
ambiguous prompt → clarification → answer → plan_ready
locator failure → recovery UI → update_locator → backend validates → retry
multi-step plan → strict cursor → recorded/code order correct
replay smoke → replay_started → replay_result
```

## 5. Negative E2E cases

```text
LLM proposes invalid plan → no executable frontend plan
frontend sends stale confirm → backend rejects → UI shows rejection
locator specialist suggests wrong locator → backend blocks → recovery UI appears
backend emits malformed event → frontend diagnostic, no fake state
recording fails → no code_update pretending success
unsupported upload/iframe → capability_gap
```

## 6. Boundary E2E cases

```text
WebSocket reconnect mid-run
correction and confirm sent close together
stop_run during execution
duplicate command sent from UI
LLM retry after schema failure
DOM changes between plan and execution
large DOM compressed before planning
long code_update displayed safely
```

## 7. Edge E2E cases

```text
weak DOM + ambiguous target + user feedback correction
exact text assertion in code block after tab switch
modal opens after click and blocks next step
dynamic dropdown rendered in portal
wrong page after navigation and replay attempted
hidden mobile/desktop duplicate candidate
toast disappears before assertion
```

## 8. Artifact requirements

Every failed E2E must produce:
```text
events.ndjson
commands.json
rejections.json where applicable
backend.log
frontend.log
browser-console.log where applicable
screenshots
trace-summary.txt or summary.md
payloads/plan-ready.json where applicable
payloads/recorded-step.json where applicable
payloads/code-update.json where applicable
payloads/replay-result.json where applicable
test-result.json
```

For pass runs, at minimum:
```text
events.ndjson
commands.json
summary.md
test-result.json
```

## 9. Gate rules

E2E acceptance requires:
```text
backend event truth asserted
frontend visible state asserted
target page effect/assertion verified
artifact bundle generated
no architecture invariant violated
```

A UI-only pass is not enough. A backend-only pass is not enough.
