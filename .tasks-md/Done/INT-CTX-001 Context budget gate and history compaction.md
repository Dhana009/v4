# INT-CTX-001 Context budget gate and history compaction

Status: Done
Sprint: Sprint 3
Type: Story
Owner: LLM Runtime / Context Manager
Priority: P0

## Source docs

- Complete LLM Mode Runtime Policy Spec
- PRD v2.3 LLM Runtime
- Sprint 3 cost optimization plan

## Problem / Goal

Context sent to the LLM can include accumulated message history, tool outputs, and DOM extraction results.

This causes large input-token usage, especially during repeated E2E runs.

Goal:

Before every LLM call, enforce a context budget gate that decides what is included, summarized, capped, or excluded.

## Scope

Every LLM call should declare or record:

- purpose
- context_level
- input_token_estimate
- included_context
- excluded_context
- reason_for_inclusion
- budget_status

Rules:

- Never send full raw DOM by default.
- Never send full conversation history by default.
- Summarize/cap dom_extract and tool outputs before resending.
- Exclude irrelevant old tool outputs.
- Escalate context level only when required and logged.

## Out of scope

- Full semantic memory system
- Multi-model routing
- Vector database or embedding store
- Full trace UI redesign

## Required tests

- Test large DOM/tool output is capped or summarized before next LLM call.
- Test full raw DOM is excluded unless L5 escalation is explicitly allowed.
- Test full message history is compacted when over budget.
- Test context budget metadata is emitted.
- Test budget exceeded causes compaction instead of sending oversized prompt.

## Acceptance criteria

- No simple E2E call sends raw full DOM/history by default.
- Context report shows included/excluded content.
- Token report shows lower message/history/DOM token contribution.
- Existing 5 E2E tests still pass.

## Default context budgets

Initial Sprint 3 budget policy:

- Reuse `PROTECTED_HISTORY_TOKEN_THRESHOLD = 6000` from `runtime/history_manager.py` as the default message-history cap.
- Cap DOM/tool result re-inclusion at 800 tokens per result.
- Full raw DOM requires explicit L5 escalation.
- Budget gate must emit:

```
budget_status = ok | capped | compacted | escalated
```

Rules:

- `ok`: context is within budget.
- `capped`: individual tool/DOM result was trimmed.
- `compacted`: history was summarized/compacted.
- `escalated`: larger context was explicitly allowed by purpose/policy.

## Evidence

Phase 0 context budgeting foundation complete.
Live E2E diagnosis shows the remaining work is purpose-specific context selection and tool-result summarization in the live path.

## Notes

This is the context-budget foundation.
Live-purpose context windows and summarization continue in INT-CTX-001B and INT-CTX-001C.
