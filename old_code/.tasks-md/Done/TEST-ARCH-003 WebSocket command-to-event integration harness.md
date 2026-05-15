# TEST-ARCH-003 WebSocket command-to-event integration harness

Status: Done
Sprint: Sprint 3.5
Type: Integration Test
Owner: Backend Integration
Priority: P0
Started: 2026-05-09

## Problem

We need a cheap backend integration harness proving command -> backend normalization -> event/rejection behavior without paid E2E, real browser, or real LLM.

## Source / architecture rule

Frontend sends typed commands. Backend validates commands and emits typed backend events or runtime_rejected. Backend owns runtime truth.

## Scope

Build a non-paid test harness that can simulate:

- WebSocket command input
- command normalization
- backend queue handoff
- runtime_rejected response
- stale/late command rejection
- session_state behavior if applicable

Use fake/stub AgentLoop and fake browser/page objects where needed.

## Out of scope

- real Playwright browser
- paid LLM calls
- full frontend UI
- broad server refactor

## Required tests

- valid command enters backend path
- malformed command emits runtime_rejected
- unknown command emits runtime_rejected
- stale run_id command is rejected
- late command after completion is rejected
- command metadata/correlation id is preserved if supported

## Acceptance criteria

- cheap tests prove command-to-event/rejection path
- no paid E2E required
- no real browser required
- existing command contract tests still pass

## Cost-aware verification plan

Run focused integration tests only.
No tests/e2e.

## Evidence

- tests added:
  - `tests/test_websocket_command_event_integration.py`
- commands run:
  - `python -m py_compile server.py runtime/event_contracts.py tests/test_websocket_command_event_integration.py`
  - `python -m pytest tests/test_websocket_command_event_integration.py -q`
  - `python -m pytest tests/test_command_contract.py tests/test_process_boundary_contract.py tests/test_late_event_contract.py -q`
- results:
  - compile passed
  - websocket integration harness: `5 passed`
  - focused regression suites: `23 passed`
- command/rejection paths covered:
  - malformed canonical command -> `runtime_rejected`
  - unknown command -> `runtime_rejected`
  - stale `run_id` command -> `runtime_rejected`
  - completed-run correction command -> backend rejection via confirmation consumer
  - valid canonical correction preserves command correlation before queue forwarding

## Implementation summary

- cheap backend websocket harness added
- no paid E2E used
- no real browser or LLM used
- no product behavior changed
