# Skill: Memory and Human Feedback

## Purpose
Make the agent stateful, human-guided, and token-efficient without sending full history every time.

## When to use
Use for conversation_state, memory retrieval, plan versions, rejected decisions, context condensation, human clarification, skill memory, trace of memory usage.

## Source of truth
- LLM Runtime Policy Memory and Human Feedback section
- Hermes-style memory/context strategy adapted to AutoWorkbench
- Backend/UI state contract

## Non-negotiable rules
1. Human feedback is preferred over guessing when ambiguity is real.
2. Stored memory is not prompt context.
3. Backend stores durable useful memory.
4. LLM receives only selected relevant memory.
5. Rejected decisions must be remembered.
6. Artifacts are passed by reference/summary, not pasted by default.
7. Memory can guide LLM, but backend validation still owns truth.
8. Trace must show what memory was retrieved and why.
9. Do not let memory override backend validation or current evidence.

## Memory layers
```text
working_memory
session_memory
artifact_memory
project_memory
skill_memory
```

## Safe LLM outputs
Every LLM purpose may return:
```text
need_user_input
need_more_context
cannot_safely_continue
capability_gap
```

## Required implementation behavior
- Store conversation summaries and decisions.
- Preserve accepted/rejected plans/locators/permissions.
- Retrieve memory by LLM purpose.
- Condense older chat into structured summaries.
- Keep unresolved items explicit.
- Log memory_scope_used, memory_items_retrieved, artifact_refs_used, token estimate.

## Required tests
- memory retrieval per purpose
- rejected locator/plan not repeated
- context condensation
- LLM prompt excludes full history by default
- trace shows memory usage
- human feedback output handling

## Verification commands
```bash
python -m pytest tests/test_*memory* tests/test_*context* -q
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- prompt includes full history by default
- rejected user decision is ignored
- LLM guesses where user input is required
- memory overrides backend validation
- memory retrieval is not traceable

## Reporting format
Report:
1. Memory layer affected
2. Retrieval policy
3. Human feedback behavior
4. Tests/results
5. Token/context impact
