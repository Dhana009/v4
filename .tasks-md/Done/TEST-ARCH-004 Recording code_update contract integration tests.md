# TEST-ARCH-004 Recording code_update contract integration tests

Status: Done
Sprint: Sprint 3.5
Type: Integration Test
Owner: Recording / Codegen
Priority: P1
Started: 2026-05-09

## Problem

Recording/code_update are well covered at helper level, but we need one backend integration sequence proving step_recorded -> code_update -> run_completed from backend-owned evidence.

## Source / architecture rule

Recording and code_update must be backend-evidence-backed. LLM cannot invent successful recorded steps.

## Scope

Add cheap integration tests for:

- deterministic click recording
- deterministic assertion recording
- corrected multi-child plan recording if feasible
- failed/unresolved child does not produce code_update

## Out of scope

- paid LLM
- real browser E2E
- broad codegen redesign

## Required tests

- step_recorded emitted after successful execution evidence
- code_update emitted after step_recorded
- expected_outcome remains parent metadata
- failed child does not produce trusted generated line
- multi-child order is preserved

## Acceptance criteria

- recording/code_update path is integration-tested
- backend evidence requirement is enforced
- focused tests pass

## Cost-aware verification plan

No paid E2E.
Use fake execution evidence.

## Decision

- Recording/code_update contract:
  - already fully covered by existing focused non-E2E suites
  - no new test file was needed without duplicating existing enforcement
- Evidence-backed code_update rule:
  - `code_update` is emitted only from backend recorded child evidence or not emitted at all
  - failed, blocked, or incomplete child evidence cannot become trusted `code_update`
- expected_outcome rule:
  - `expected_outcome` remains parent metadata only
  - it is excluded from recorded child payloads and does not become assertion target/value unless the confirmed assertion contract explicitly carries assertion values
- Ordering rule:
  - `step_recorded -> code_update -> run_completed`
  - multi-child `code_update` line order follows confirmed recorded child order

## Tests added

- none
- existing focused suites already covered the required contract slice without gaps worth duplicating

## Commands run

- `python -m py_compile tests/test_recording_codegen_truth_contract.py tests/test_recorded_step_model.py tests/test_code_update.py tests/test_backend_event_sequences.py`
- `python -m pytest tests/test_recording_codegen_truth_contract.py -q`
- `python -m pytest tests/test_recorded_step_model.py tests/test_code_update.py tests/test_backend_event_sequences.py -q`

## Results

- compile passed
- `tests/test_recording_codegen_truth_contract.py`: `9 passed`
- `tests/test_recorded_step_model.py tests/test_code_update.py tests/test_backend_event_sequences.py`: `26 passed`

## Interpretation

- What the tests prove:
  - backend action evidence is required before `step_recorded` becomes truth
  - successful recording emits `step_recorded`, then `code_update`, then `run_completed`
  - `code_update` line generation follows confirmed child evidence and preserved child order
  - `expected_outcome` stays on parent metadata and is excluded from recorded child payloads
  - broad page text or LLM-like prose does not become trusted `code_update` when confirmed evidence is specific or missing
- What remains a gap:
  - there is still no broader live browser integration in this slice, by design
  - Sprint 3.5 still needs fast-path vs fake-LLM integration parity from `TEST-ARCH-005`

## Changed files

- `.tasks-md/Done/TEST-ARCH-004 Recording code_update contract integration tests.md`

## Commit

- pending
