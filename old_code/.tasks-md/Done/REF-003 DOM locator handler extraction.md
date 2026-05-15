# REF-003 DOM locator handler extraction

Status: Done
Sprint: Post Sprint 3.5
Owner: Runtime Architecture
Source docs:
- REF-AUDIT-001 Agent Modularization Map
- REF-AUDIT-002 Characterization tests before extraction
- REF-001 review gate

## Problem / goal

Extract the already-characterized DOM/locator tool handler seam out of `agent.py` without changing advisory locator behavior, DOM extraction payloads, or backend validation requirements.

## Scope

- `_tool_dom_extract`
- `_tool_locator_find`
- `_tool_locator_validate`
- thin adapter methods in `agent.py`

## Out of scope

- Lifecycle orchestration
- Correction flow
- Confirmed execution
- Recording/code_update
- Main run loop
- Frontend
- Snapshot/archive redesign

## Required tests

- `python -m py_compile agent.py runtime/agent_locator_handlers.py`
- `python -m pytest tests/test_agent_locator_handler_contract.py tests/test_agent_dom_extract_contract.py -q`
- `python -m pytest tests/test_dom_locator_contracts.py tests/test_dom_locator_advanced_contracts.py -q`
- `python -m pytest tests/test_deterministic_fast_path.py tests/test_backend_event_sequences.py -q`

## Acceptance criteria

- `agent.py` contains less DOM/locator handler logic than before
- DOM extraction output is unchanged
- locator candidates remain advisory
- backend/browser validation remains required before execution
- focused tests pass

## Evidence

- Extracted `_tool_dom_extract`, `_tool_locator_find`, and `_tool_locator_validate` into `runtime/agent_locator_handlers.py`.
- Reduced `agent.py` to thin adapter methods for the DOM/locator tool-handler seam.
- Preserved advisory locator semantics, DOM extraction payload shape, and backend validation requirements.

## Verification commands/results

- `python -m py_compile agent.py runtime/agent_locator_handlers.py`
  - pass
- `python -m pytest tests/test_agent_locator_handler_contract.py tests/test_agent_dom_extract_contract.py -q`
  - `7 passed`
- `python -m pytest tests/test_dom_locator_contracts.py tests/test_dom_locator_advanced_contracts.py -q`
  - `17 passed`
- `python -m pytest tests/test_deterministic_fast_path.py tests/test_backend_event_sequences.py -q`
  - `35 passed`
