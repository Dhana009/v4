# TEST-ARCH-003 WebSocket command-to-event integration harness

Status: Planning
Sprint: Sprint 3.5
Type: Integration Test
Owner: Backend Integration
Priority: P0

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
