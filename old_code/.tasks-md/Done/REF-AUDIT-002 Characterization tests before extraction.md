# REF-AUDIT-002 Characterization tests before extraction

Status: Done
Sprint: Sprint 3.5
Type: Refactor Readiness
Owner: Runtime Architecture
Priority: P1

## Problem

agent.py should be modularized, but extraction is risky unless behavior is characterized first.

## Source / architecture rule

Refactor must preserve backend truth, event contracts, confirmation gate, recording/code_update, LLM policy, and replay behavior.

## Scope

Define and add characterization tests required before any extraction.

Areas:

- plan_ready builder behavior
- correction state behavior
- confirmed execution validation
- recording/code_update payloads
- deterministic fast path
- DOM/locator handlers
- replay/snapshot helpers

## Out of scope

- extracting modules
- rewriting agent.py
- formatting-only refactor

## Required tests

At minimum, identify or add characterization tests for first safe extraction candidate.

## Acceptance criteria

- first extraction candidate is identified
- required tests are green
- risky extractions are explicitly blocked
- no production behavior changed

## Cost-aware verification plan

Focused non-E2E tests only.

## Evidence

Decision:
- First safe extraction candidate: deterministic fast path gateway, specifically the `_try_deterministic_fast_path` and `_execute_deterministic_fast_path_confirmed_plan` seam as a later `runtime/fast_path_gateway.py` slice.
- Extraction readiness: ready for a small behavior-preserving extraction later, because qualification behavior, confirmation gating, confirmed-plan compatibility, and post-confirmation recording/code_update behavior are already characterized by focused non-E2E tests.
- Explicitly not ready for extraction: lifecycle orchestration, correction flow, confirmed execution contract, recording/codegen, and the main run loop remain high-risk and should not move yet.
- Human approval still required before extraction: yes

Characterization evidence:
- deterministic fast path:
  - `tests/test_deterministic_fast_path.py` proves stable qualification and non-qualification for simple vs compound/ambiguous inputs, backend-compatible deterministic plan shape, no auto-execution before confirmation, no LLM message use during confirmed fast-path execution, and backend-owned `step_recorded`/`code_update` after confirmation.
  - `tests/test_backend_event_sequences.py` proves deterministic click and assertion flows still emit `plan_ready -> step_recorded -> code_update -> run_completed`, and proves the ambiguous fake-LLM path stays at `plan_ready` before confirmation.
- DOM/locator:
  - `tests/test_agent_locator_handler_contract.py`, `tests/test_agent_dom_extract_contract.py`, `tests/test_dom_locator_contracts.py`, and `tests/test_dom_locator_advanced_contracts.py` prove locator candidates remain advisory, unique-vs-ambiguous classification is stable, scope suggestions appear on multiple matches, and DOM extraction remains backend-owned structured context rather than execution truth.
- snapshot/replay:
  - `tests/test_snapshot_archive_contract.py` proves malformed archive input is rejected safely, valid snapshots preserve recorded step metadata, expected/observed outcomes remain backend-owned, and unresolved/failed steps do not become completed.
  - `tests/test_replay_one.py` proves replay ordering follows recorded child evidence, replay preconditions block wrong-start-page execution, and artifact state is not mutated by blocked replay.
- lifecycle/correction/recording risk:
  - These areas are strongly tested but remain too coupled to the orchestration spine to extract yet. They still depend on the already-completed Sprint 3.5 contract suites and should remain blocked until the first small extraction lands cleanly.

Tests added or verified:
- No new tests added.
- Verified existing focused coverage in:
  - `tests/test_deterministic_fast_path.py`
  - `tests/test_snapshot_archive_contract.py`
  - `tests/test_agent_locator_handler_contract.py`
  - `tests/test_agent_dom_extract_contract.py`
  - `tests/test_dom_locator_contracts.py`
  - `tests/test_dom_locator_advanced_contracts.py`
  - `tests/test_backend_event_sequences.py`
  - `tests/test_recording_codegen_truth_contract.py`
  - `tests/test_replay_one.py`

Commands run:
- `python -m py_compile tests/test_deterministic_fast_path.py`
- `python -m pytest tests/test_deterministic_fast_path.py -q`
- `python -m pytest tests/test_snapshot_archive_contract.py -q`
- `python -m pytest tests/test_agent_locator_handler_contract.py tests/test_agent_dom_extract_contract.py tests/test_dom_locator_contracts.py tests/test_dom_locator_advanced_contracts.py -q`
- `python -m pytest tests/test_deterministic_fast_path.py tests/test_recording_codegen_truth_contract.py tests/test_backend_event_sequences.py -q`

Results:
- `py_compile`: pass
- `tests/test_deterministic_fast_path.py`: `31 passed`
- `tests/test_snapshot_archive_contract.py`: `5 passed`
- DOM/locator focused suites: `24 passed`
- fast-path safety set: `44 passed`

Interpretation:
- What is now safe to extract later:
  - The deterministic fast path gateway is the safest first `agent.py` extraction candidate.
  - Snapshot/archive helpers are also well characterized and remain a reasonable follow-on candidate.
  - DOM/locator handlers are characterized enough for a later narrow extraction, but they are slightly less isolated than the deterministic fast path seam.
- What remains unsafe:
  - Lifecycle orchestration, correction flow, confirmed execution, recording/codegen, and the main run loop are still not safe first slices.
- What must be protected during extraction:
  - Fast-path qualification rules must not broaden.
  - Ambiguous input must not silently enter deterministic execution.
  - `plan_ready` must remain proposal-only before confirmation.
  - `step_recorded` and `code_update` must remain backend-evidence-backed.
  - Replay/snapshot helpers must continue to fail closed on malformed or unsafe state.

Changed files:
- `.tasks-md/Done/REF-AUDIT-002 Characterization tests before extraction.md`

Commit:
- pending
