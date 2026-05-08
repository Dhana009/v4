# TEST-DOCTRINE-001 Risk-Based TDD Doctrine

**Type:** Testing Doctrine  
**Status:** Planning  
**Priority:** P0  
**Applies To:** All AutoWorkbench implementation work  
**Owner:** Planning Brain / DEV-4 Evidence Governance  

## 1. Core rule

```text
If it is not testable, we do not build it.
If it is in the PRD, it must become a test property.
If it affects runtime truth, it must have unit + integration + regression coverage.
```

Testing is not final QA. Testing is the architecture enforcement layer.

## 2. Architecture truth model

```text
Backend = truth
LLM = reasoning/proposal
Frontend = display + command sender
DOM intelligence = candidate/context provider
Trace = evidence
Tests = enforcement layer
```

Forbidden:
```text
LLM owns runtime truth
frontend owns lifecycle truth
trace owns runtime truth
DOM candidate executes without backend/browser validation
recording/codegen from LLM prose
expected_outcome becomes assertion target/value
P1/P2 future behavior silently becomes MVP
```

## 3. Test derivation method

```text
source rule
→ architecture invariant
→ test property
→ positive/negative/boundary/edge/regression cases
→ automation layer
→ evidence/artifact
```

Example:
```text
Source rule: Backend owns execution truth.
Invariant: No browser execution before backend confirms active plan.
Positive: valid confirm allows execution.
Negative: LLM action_click before confirmation rejected.
Boundary: duplicate confirm handled safely.
Edge: correction creates new plan_version; old confirm rejected.
Regression: plan_ready must not overwrite active execution.
```

## 4. Five-angle test model

| Angle | Question |
|---|---|
| Positive | Does the valid path work? |
| Negative | Does invalid behavior fail safely? |
| Boundary | What happens with duplicate/stale/missing/partial/out-of-order data? |
| Edge | What happens in messy real-world situations? |
| Regression | Which old bugs must never return? |

A feature with only positive tests is not implementation-ready.

## 5. Mandatory P0 test properties

```text
1. No execution before confirmation.
2. Backend rejects stale plan_version.
3. LLM cannot emit runtime truth.
4. Frontend cannot infer lifecycle truth.
5. Trace cannot become runtime truth.
6. Every command has typed validation/rejection.
7. Every event has typed envelope and causal order.
8. Locator specialist output cannot execute without backend/browser validation.
9. Ambiguous locator blocks execution.
10. Recovery open blocks run_completed.
11. Recording requires execution evidence.
12. code_update follows step_recorded.
13. expected_outcome stays metadata only.
14. visible assertion does not become click.
15. exact_text assertion keeps expected_value.
16. Correction cannot silently drop/reorder children.
17. Multi-step strict cursor prevents contamination.
18. Unsupported capability becomes typed gap.
19. Every UI failure state gives a next safe action.
20. Every failed E2E produces artifacts.
```

## 6. Coverage policy

```text
95% line coverage for new/changed backend/runtime modules
95% line coverage for deterministic LLM/DOM controller modules
branch coverage required for validators/reducers/state machines
100% schema coverage for event/command/LLM contracts
100% known-regression coverage
E2E coverage for all MVP flows
artifact evidence for failed E2E runs
```

Line coverage alone is insufficient. Also require:
```text
state-transition coverage
event-sequence coverage
schema-failure coverage
fixture-pattern coverage
negative-path coverage
recovery-path coverage
idempotency/race-condition coverage
```

## 7. Layer doctrine

### Backend
Test state machines, command validation, event order, recording, codegen, completion, replay, gaps, trace, idempotency, and backward compatibility.

### LLM + DOM
Test purpose registry, tools by phase, skill/context loading, schema fail-closed, DOM extraction, compression, main/specialist handoff, user feedback, token budget, and fixture coverage.

### Frontend
Test event-backed rendering, typed commands, plan/recovery UI, recorded/code panels, picker, trace, no-deadlock states, accessibility hooks.

### E2E
Test full causal chains with backend event truth + frontend visible state + browser evidence + artifacts.

## 8. Real-world fixture doctrine

CI must use local deterministic fixtures inspired by real-world patterns:
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

Live sites are optional/manual only.

## 9. Merge gate rules

No PR/merge unless:
```text
tests were written or updated before implementation
positive and negative tests exist
boundary/edge cases are covered where relevant
known regressions are protected
coverage threshold is met
E2E artifacts exist for product-level changes
architecture invariants are not violated
reviewer can map tests back to source rules
```

## 10. Stop conditions

Stop implementation if:
```text
a requirement cannot be tested
backend truth ownership is unclear
frontend/LLM/trace would own truth
event/command schema is unclear
LLM output cannot be schema-validated
DOM fixture cannot represent real risk
failure state has no next safe action
coverage cannot be measured
E2E artifacts cannot be captured
```
