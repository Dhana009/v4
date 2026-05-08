# INT-CTX-001B Purpose-specific context windows

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: Context Manager / LLM Runtime
Priority: P1

## Problem

ContextManager prepares context similarly for all calls and history/tool result tokens grow across calls.

## Source / architecture rule

- runtime/context_manager.py
- runtime/history_manager.py
- Complete LLM Mode Runtime Policy Spec
- Sprint 3 token diagnosis report

## Scope

Add context window rules by purpose:
- simple planning: current step + picked element + current page summary only
- locator specialist: focused locator candidates + local context only
- plan_diff_editor: current plan + user correction only
- recovery: failure context + recent evidence only
- broad main_orchestrator fallback: capped history

## Out of scope

- Semantic vector memory
- Full trace UI
- Multi-model routing

## Required tests

- simple planning excludes old tool outputs
- locator purpose receives only focused locator context
- plan_diff_editor excludes DOM history
- correction history is capped

## Acceptance criteria

- message_history_tokens reduce
- no quality regression in focused tests

## Cost-aware verification plan

Run context manager unit tests.
One E2E smoke only if needed.

## Evidence

To be filled during implementation.

## Notes

This is the history growth control point.
