# REF-001 Deterministic fast path gateway extraction

Status: Done
Sprint: Post Sprint 3.5
Owner: Runtime Architecture
Source docs:
- REF-AUDIT-001 Agent Modularization Map
- REF-AUDIT-002 Characterization tests before extraction

## Problem / goal

`agent.py` still owns deterministic fast path gateway wiring. The goal is to extract only that gateway seam into a focused runtime module without changing qualification behavior, confirmation gating, confirmed execution compatibility, or recording/code_update flow.

## Scope

- Extract deterministic fast path gateway decision/wiring out of `agent.py`
- Keep `agent.py` as a thin caller
- Preserve all current outputs and logging semantics as closely as possible

## Out of scope

- No lifecycle orchestration refactor
- No correction flow refactor
- No confirmed execution refactor
- No recording/codegen refactor
- No frontend changes
- No paid E2E or live LLM

## Required tests

- `python -m py_compile agent.py runtime/deterministic_fast_path.py`
- `python -m py_compile runtime/deterministic_fast_path_gateway.py`
- `python -m pytest tests/test_deterministic_fast_path.py -q`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_lifecycle_checkpoint_contract.py tests/test_recording_codegen_truth_contract.py -q`
- `python -m pytest tests/test_recorded_step_model.py tests/test_code_update.py -q`

## Acceptance criteria

- `agent.py` contains less deterministic fast path gateway logic than before
- deterministic fast path behavior is unchanged
- ambiguous/compound input still does not qualify
- no execution occurs before confirmation
- confirmed execution path remains unchanged
- focused tests pass

## Evidence

- Extracted deterministic fast path gateway wiring into `runtime/deterministic_fast_path_gateway.py`.
- Reduced `agent.py` to a thin `_try_deterministic_fast_path` adapter that calls the extracted gateway.
- Left `_execute_deterministic_fast_path_confirmed_plan` in `agent.py` unchanged.
- Preserved confirmation gating, correction fallback, and backend-owned post-confirmation recording/code_update flow.

## Verification commands/results

- `python -m py_compile agent.py runtime/deterministic_fast_path.py runtime/deterministic_fast_path_gateway.py`
  - pass
- `python -m pytest tests/test_deterministic_fast_path.py -q`
  - `31 passed`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_lifecycle_checkpoint_contract.py tests/test_recording_codegen_truth_contract.py -q`
  - `17 passed`
- `python -m pytest tests/test_recorded_step_model.py tests/test_code_update.py -q`
  - `22 passed`
