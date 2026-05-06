# Skill: Contract Testing

## Purpose
Verify backend/frontend/LLM contracts independently from full E2E flows.

## When to use
Use for typed events, commands, schemas, LLM output schemas, backend state objects, frontend state rendering, WebSocket payloads, tool policies.

## Source of truth
- Typed Event Contract
- Backend/UI state contract
- LLM Runtime Policy output schemas
- Frontend/UI event mapping

## Non-negotiable rules
1. Important contracts need tests outside full E2E.
2. Contract tests should validate payload shape and required fields.
3. Invalid/malformed payloads should fail safely.
4. LLM schema validation must be tested.
5. Frontend should not rely on missing optional fields without fallback.
6. Contract changes must list affected producers/consumers.

## Required contract areas
```text
commands
events
state objects
LLM schemas
tool policies
context policies
skill policies
replay results
code_update
locator_update_result
permission/test_data events
```

## Required tests
- Backend schema/unit tests
- Frontend handler tests where available
- Snapshot/sample payload tests
- Invalid payload tests
- Compatibility tests for old/new fields if needed

## Verification commands
```bash
python -m pytest tests/test_*contract* tests/test_*schema* tests/test_*ws* -q
npm run build
```

## Stop conditions
Stop if:
- event producer/consumer mismatch found
- required fields not defined
- schema is only documented but not tested
- frontend handler accepts ambiguous state
- backend command validation is missing

## Reporting format
Report:
1. Contracts tested
2. Payload examples
3. Invalid cases tested
4. Producers/consumers affected
5. Results/risks
