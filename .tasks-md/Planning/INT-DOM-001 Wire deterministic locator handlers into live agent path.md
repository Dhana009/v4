# INT-DOM-001 Wire deterministic locator handlers into live agent path

Status: Planning  
Sprint: Sprint 2  
Type: Story  
Owner: DOM / Locator  
Priority: P0  

## Source docs

- Complete LLM Mode P0 scenario spec sections on deterministic-first locator resolution and duplicate handling
- `02_LLM_RUNTIME.md`
- Existing DOM locator contract tests

## Problem / Goal

`dom_locator_contract.py` contains deterministic locator ranking, validation classification, and scoping helpers, but `agent.py` does not use them in the live locator handlers.

## Scope

Wire deterministic contract functions into existing live handler responses:

```text
locator_find -> rank_locator_candidates
locator_validate -> validate_locator_candidate
count > 1 -> include scope_candidates suggestions before LLM escalation
```

## Out of scope

```text
full locator architecture rewrite
multi-model locator specialist
frontend picker redesign
changes to runtime/dom_locator_contract.py unless a test proves contract bug
```

## Required tests

```text
test_locator_find_handler_returns_ranked_candidates
test_locator_validate_handler_returns_classification
test_scope_candidates_invoked_on_multiple_match
test_unique_deterministic_candidate_does_not_need_llm_locator_reasoning
```

## Acceptance criteria

```text
locator_find response includes ranked_candidates
locator_validate response includes classification/status/match_count
multiple matches include scope suggestions
no additional LLM calls introduced
existing DOM contract tests pass
```

## Stop conditions

```text
locator handler lacks required candidate metadata
Playwright validation result cannot be converted to validate_locator_candidate input
implementation requires broad agent.py restructuring
```

## Evidence

TBD after implementation.
