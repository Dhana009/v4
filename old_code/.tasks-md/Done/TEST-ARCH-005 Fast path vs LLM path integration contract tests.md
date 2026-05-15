# TEST-ARCH-005 Fast path vs LLM path integration contract tests

Status: Done
Sprint: Sprint 3.5
Type: Integration / Policy Test
Owner: Backend Policy
Priority: P1
Started: 2026-05-09

## Problem

Sprint 3 proved deterministic and LLM-required paths through E2E. We need cheaper integration tests proving both paths preserve backend truth without paid E2E.

## Source / architecture rule

Deterministic path should avoid LLM when safe. LLM path should trigger when intent is ambiguous/broad. Both must preserve backend confirmation, execution contract, recording, and telemetry.

## Scope

Add cheap integration tests comparing:

- deterministic picked click path
- deterministic picked assertion path
- ambiguous action path using fake/stub LLM
- broad planning fallback using fake/stub LLM if feasible

## Out of scope

- paid LLM
- real browser E2E
- frontend UI

## Required tests

- deterministic path uses no model call
- ambiguous path uses fake model call
- fast path does not trigger for ambiguous input
- both paths emit compatible plan_ready structures
- both paths require confirmation before execution

## Acceptance criteria

- fast path and LLM path are covered in one cheap suite
- backend truth is preserved
- telemetry/purpose behavior is asserted where possible

## Cost-aware verification plan

No paid E2E.
Use fake/stub model and fake browser.

## Evidence

Decision:
- Fast path contract: existing focused tests already prove simple click/assert/fill intents qualify for deterministic fast path, preserve backend-compatible parent/child plan shape, and do not call the LLM seam.
- LLM-required path contract: existing focused tests already prove ambiguous/broad intent does not qualify for deterministic fast path and stays proposal-only through a fake model-planning seam before confirmation.
- Confirmation gate parity: existing focused tests already prove neither path emits `step_recorded`, `code_update`, or `run_completed` before confirmation.
- Recording/code_update parity: existing focused tests already prove both paths rely on the same confirmed execution and backend evidence rules before `step_recorded` and `code_update`.

Tests added or verified:
- Verified existing coverage in `tests/test_deterministic_fast_path.py`
- Verified existing coverage in `tests/test_backend_event_sequences.py`
- Verified existing coverage in `tests/test_lifecycle_checkpoint_contract.py`
- Verified existing coverage in `tests/test_recording_codegen_truth_contract.py`

Commands run:
- `python -m py_compile tests/test_deterministic_fast_path.py tests/test_backend_event_sequences.py tests/test_lifecycle_checkpoint_contract.py tests/test_recording_codegen_truth_contract.py`
- `python -m pytest tests/test_deterministic_fast_path.py tests/test_backend_event_sequences.py tests/test_lifecycle_checkpoint_contract.py tests/test_recording_codegen_truth_contract.py -q`

Results:
- `py_compile`: pass
- focused verification suite: `48 passed`

Interpretation:
- What the tests prove:
- `tests/test_deterministic_fast_path.py` proves deterministic qualification, compound/ambiguous rejection, backend-compatible plan shape, confirmation-gate preservation, no LLM message use during fast-path execution, and confirmed-execution recording/code_update on the deterministic path.
- `tests/test_backend_event_sequences.py` proves deterministic click and assertion flows emit `plan_ready -> step_recorded -> code_update -> run_completed`, and proves the fake-LLM ambiguous flow emits only `plan_ready` before confirmation while skipping fast path.
- `tests/test_lifecycle_checkpoint_contract.py` proves the mapped backend lifecycle checkpoint contract around planning and executing phases remains backend-owned for both paths.
- `tests/test_recording_codegen_truth_contract.py` proves recording/code_update remains evidence-backed, preserves child order, and does not trust missing or incomplete execution evidence.
- What remains a gap:
- This closes the fast-path vs LLM-path contract slice without adding a new harness.
- Broader refactor-readiness still needs `REF-AUDIT-002` before any extraction work starts.

Changed files:
- `.tasks-md/Done/TEST-ARCH-005 Fast path vs LLM path integration contract tests.md`

Commit:
- pending
