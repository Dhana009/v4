# DEV-1 Recording Codegen Truth Implementation

Status: In Progress
Owner: DEV-1
Branch: `dev1/backend-isolation-contract-tests`

Current focus:
- Recording/codegen truth implementation
- Current contract test slice: `tests/test_recording_codegen_truth_contract.py`

Current gap:
- `agent.py::_build_code_update_payload(...)` can still fall back to `generated_line` when child evidence is unresolved or failed.

Next implementation target:
- Require `code_update` lines to come only from successful or recorded backend child-operation evidence.

Current evidence:
- Focused backend contract slice: `50 passed, 1 xfailed` before implementation.

Boundaries:
- Backend runtime only
- No frontend
- No LLM/DOM
- No E2E harness
- No fixtures
- No broad replay repair
- No full session restore
- No trace/export work
