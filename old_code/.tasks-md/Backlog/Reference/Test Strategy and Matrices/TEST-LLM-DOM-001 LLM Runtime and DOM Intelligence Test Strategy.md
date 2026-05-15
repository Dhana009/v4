# TEST-LLM-DOM-001 LLM Runtime and DOM Intelligence Test Strategy

**Type:** Test Strategy  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-2 LLM Runtime + DOM/Locator, DEV-4 Fixtures/E2E  

## 1. Purpose

The LLM layer is a controlled reasoning system, not a runtime owner.

Tests must prove:
```text
LLM output is constrained
DOM context is scoped
locator candidates are validated
ambiguity blocks execution
failure routes recovery/user feedback
token budget is controlled
real-world messy pages are covered
```

## 2. Pipeline under test

```text
user intent
→ page exploration
→ DOM extraction
→ DOM compression/context selection
→ main planner / locator specialist / correction / recovery LLM
→ schema validation
→ backend validation
→ browser locator validation
→ execution or rejection/recovery
```

## 3. Runtime controller tests

```text
purpose registry validates known purposes
unknown purpose rejected
purpose exposes only allowed tools
purpose loads only required skills
purpose has token budget
purpose has model route
purpose has schema where structured output is required
runtime-impacting purpose has backend validator
invalid schema retries once
invalid schema twice fails closed
schema-valid but backend-invalid output rejected
```

P0 purposes:
```text
intent_classifier
journey_planner
plan_correction
locator_specialist
recovery_diagnoser
codegen_reviewer
trace_summarizer
```

## 4. Tool phase-gating tests

```text
LLM action_click before confirmation blocked
LLM action_assert before confirmation blocked
LLM send_to_overlay(step_recorded) blocked/ignored
LLM run_completed blocked/impossible
LLM plan_ready during execution rejected
LLM correction during execution routed/rejected by policy
```

## 5. Failure-injection tests

Inject:
```text
invalid JSON
missing step_id
missing operation_id
invalid operation type
click instead of assertion
exact_text missing expected_value
step_recorded output
run_completed output
bad correction diff
silent child drop
low-confidence locator
hallucinated locator
unsupported capability claimed as supported
```

Expected:
```text
schema rejection
retry once
fail closed
backend rejection
clarification_needed
recovery_needed
capability_gap
no runtime mutation
```

## 6. DOM extraction tests

Extractor must:
```text
extract interactive elements
extract roles/accessibility names
extract labels/placeholders
extract buttons/links/inputs/selects
extract code/pre/text blocks
extract section/card/row/form/dialog ancestors
mark hidden/disabled/stale candidates
preserve useful text summary
avoid dumping massive raw DOM
```

## 7. DOM compression / context selection tests

```text
main LLM gets relevant page summary, not raw full DOM
locator specialist gets focused candidate context
backend receives stable candidate IDs/locator refs
irrelevant sections are excluded or summarized
large DOM is chunked/compressed
user intent controls DOM slice selection
```

Boundary:
```text
DOM summary missing target → ask more context or specialist route
DOM summary too noisy → token budget guard triggers
wrong section selected → backend validation/ambiguity blocks execution
```

## 8. Main LLM vs locator specialist tests

```text
main LLM does not receive raw full DOM unnecessarily
locator specialist receives scoped DOM only
specialist output includes confidence and candidate IDs
specialist output can be rejected
backend validation is mandatory
wrong specialist suggestion does not execute
specialist disagreement/low confidence routes ask_user/recovery
```

## 9. Planner/correction/recovery tests

Planner:
```text
simple click → click operation
visible assertion → assertion operation, not click
exact text → exact_text with expected_value
multi-step → ordered stable IDs
ambiguous → clarification_needed
unsupported → capability_gap/ask_user
```

Correction:
```text
add assertion before click
replace target
change expected text
remove step explicitly
reorder explicitly
reject silent child drop
reject whole-plan overwrite
reject stale plan_version
```

Recovery:
```text
locator not found → ask_user/update_locator
multiple matches → ask_user with candidates
hidden/disabled → recovery
wrong page → precondition/recovery
modal/dropdown state → dynamic recovery
iframe/upload/permission → capability_gap
diagnoser cannot decide success
```

## 10. Fixture classes

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

## 11. Mandatory regressions

```text
1. LLM cannot execute before confirmation.
2. LLM cannot emit step_recorded.
3. LLM cannot emit run_completed.
4. Invalid planner schema fails closed.
5. Correction cannot silently drop/reorder children.
6. Assertion intent does not become click.
7. Exact text assertion keeps expected_value.
8. Locator specialist suggestion requires backend validation.
9. Duplicate CTA routes ambiguity.
10. Hidden candidate is not executed.
11. Weak nested span resolves to useful ancestor.
12. Large DOM is compressed, not fully dumped.
13. Too-little DOM routes more-context/clarification.
14. Wrong-page locator routes recovery.
15. Unsupported iframe/upload produces capability_gap.
```

## 12. Coverage

```text
95% coverage for deterministic LLM/DOM controller modules
100% schema coverage for LLM output contracts
100% negative coverage for runtime-impacting invalid schemas
fixture coverage for every supported DOM pattern
typed gap tests for unsupported patterns
token-budget tests for large DOM/context
```
