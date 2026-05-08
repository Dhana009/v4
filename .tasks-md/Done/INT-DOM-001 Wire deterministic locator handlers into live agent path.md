# INT-DOM-001 Wire deterministic locator handlers into live agent path

Status: Done  
Sprint: Sprint 2  
Type: Story  
Owner: DOM / Locator  
Priority: P0  
Started: 2026-05-08 16:45 IST  
Completed: 2026-05-08 17:00 IST  

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

## Implementation summary

- Added import: `from runtime.dom_locator_contract import rank_locator_candidates, validate_locator_candidate, scope_candidates` (agent.py line 21).
- `_tool_locator_find`: calls `rank_locator_candidates(candidates, target_text)` and includes result as `ranked_candidates` in both found and not-found responses. On not-found, calls `scope_candidates(candidates)` and includes result as `scope_suggestions`.
- `_tool_locator_validate`: builds match stubs from the resolved count, calls `validate_locator_candidate(locator_ref, matches, visible_matches, page_url, expected_value)`, and includes `classification`, `status`, `match_count` in the response alongside existing `valid`/`count` fields.
- No new LLM calls introduced. Existing response fields preserved for backward compatibility.

## Tests added

```text
tests/test_agent_locator_handler_contract.py (5 tests):
- test_locator_find_handler_returns_ranked_candidates
- test_locator_validate_handler_returns_classification
- test_scope_candidates_invoked_on_multiple_match
- test_unique_deterministic_candidate_does_not_need_llm_locator_reasoning
- test_locator_validate_not_found_returns_not_found_classification
```

## Verification

```text
python -m py_compile agent.py runtime/dom_locator_contract.py  → OK
python -m pytest tests/test_agent_locator_handler_contract.py -q  → 5 passed
python -m pytest tests/test_dom_locator_contracts.py tests/test_dom_locator_advanced_contracts.py -q  → all passed
python -m pytest (full contract suite)  → 137 passed
python -m pytest tests/e2e/ -q -s  → 4 passed (no regression)
```

## Commit

TBD — committed with "feat: wire deterministic locator handlers into agent path"
