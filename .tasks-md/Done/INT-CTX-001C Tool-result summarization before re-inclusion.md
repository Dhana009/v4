# INT-CTX-001C Tool-result summarization before re-inclusion

Status: Done
Sprint: Sprint 3
Type: Story
Owner: Context Manager / DOM Intelligence
Priority: P1
Started: 2026-05-08 20:58 IST

## Problem

DOM/tool results are resent and grow across calls.

## Source / architecture rule

- runtime/context_manager.py
- runtime/page_intelligence.py
- runtime/telemetry.py
- Complete LLM Mode Runtime Policy Spec
- Sprint 3 token diagnosis report

## Scope

Before re-including tool results in LLM context:
- summarize DOM/page intelligence results
- cap tool output
- remove raw HTML
- keep backend-side raw evidence separately
- include only latest relevant tool result for current purpose

## Out of scope

- Removing evidence storage
- Removing locator validation
- Frontend changes

## Required tests

- raw DOM is not re-included by default
- summarized tool result is included
- old irrelevant tool result is excluded
- backend-side evidence remains available

## Acceptance criteria

- dom_or_tool_result_tokens reduce
- locator/execution still works

## Cost-aware verification plan

Run context/page-intelligence tests.
No full E2E until final acceptance.

## Evidence

- `python -m py_compile runtime/context_manager.py tests/test_context_manager.py tests/test_context_budget_gate.py`
- `python -m pytest tests/test_context_manager.py tests/test_context_budget_gate.py -q`
  - Result: `24 passed`

## Notes

This keeps repeated tool outputs from bloating follow-up calls.

Implementation summary:
- Replaced blunt tool-result truncation with pre-cap summarization
- Removed backend-only raw DOM fields like `_raw_elements` from prompt copies
- Collapsed raw HTML tool payloads into compact page-intelligence summaries
- Kept original source messages untouched so backend-side raw evidence remains available
