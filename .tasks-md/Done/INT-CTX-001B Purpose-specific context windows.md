# INT-CTX-001B Purpose-specific context windows

Status: Done
Sprint: Sprint 3
Type: Story
Owner: Context Manager / LLM Runtime
Priority: P1
Started: 2026-05-08 20:45 IST

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

- `python -m py_compile runtime/context_manager.py tests/test_context_manager.py tests/test_context_budget_gate.py`
- `python -m pytest tests/test_context_manager.py tests/test_context_budget_gate.py -q`
  - Result: `21 passed`

## Notes

This is the history growth control point.

Implementation summary:
- Added purpose-specific compact windows in `ContextManager.prepare_messages()`
- `step_plan_normalizer` keeps system + original intent + latest planning tool chain
- `plan_diff_editor` keeps correction-only conversational context and drops DOM/tool history
- `locator_specialist` keeps only the latest locator chain plus local context
- `recovery_diagnoser` keeps failure/recovery evidence plus recent messages
