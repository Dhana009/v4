# Skill: AutoWorkbench Architecture Contract

## Purpose
Protect the core AutoWorkbench architecture from drift during implementation.

## When to use
Use for every backend, frontend, LLM, test, refactor, replay, codegen, locator, and UI task.

## Source of truth
- PRD v2.3 modular pack
- Complete LLM Mode architecture spec
- Frontend/UI spec
- LLM Runtime Policy spec
- Latest handoff notes

## Non-negotiable rules
1. LLM proposes, reasons, decomposes, explains, and suggests repairs.
2. Backend owns runtime truth, lifecycle, execution, recording, validation, replay, and code_update.
3. Frontend renders typed backend state and collects user input.
4. Frontend must not infer lifecycle truth from LLM prose, CSS, local strings, or timing.
5. All frontend/backend communication must use typed events and typed commands.
6. Confirmed plan is the execution contract.
7. Recorded steps are execution evidence/history, not draft intent.
8. Deterministic backend checks must happen before LLM calls when possible.
9. No ad-hoc direct LLM calls. All LLM usage must go through the LLM Runtime Controller.
10. Do not silently drop, reorder, mutate, or replace steps/operations.
11. expected_outcome is parent/step metadata, not locator/assertion target/value.
12. Unsupported capabilities must produce capability_gap or a clear blocking event, not fake success.
13. Do not change architecture from intuition; use the PRD/specs and backend evidence.

## Required implementation behavior
- Read the smallest relevant PRD/spec section before changing code.
- Identify the source of truth for the behavior being changed.
- Preserve stable IDs across pending → plan → confirmed → execution → recording → replay.
- Add typed state/events rather than implicit UI state or prose-based state.
- Prefer narrow changes with regression coverage.
- If a change touches lifecycle, recording, execution, frontend state, or LLM routing, explicitly describe which contract it affects.

## Required tests
At minimum, add or update tests that prove:
- backend remains source of truth
- frontend receives typed state/events
- confirmed plan cannot be bypassed
- invalid/unsupported behavior fails safely
- no silent step/operation loss occurs

## Verification commands
Use project-appropriate focused commands. Prefer:
```bash
python -m pytest <focused-tests> -q
```
For frontend:
```bash
npm run build
```
For browser/E2E:
```bash
python -m pytest tests/e2e/<focused_flow>.py -q -s
```

## Stop conditions
Stop and report evidence if:
- required evidence is missing, unclear, or contradictory
- PRD/spec conflicts with current implementation
- implementation requires broad rewrite
- frontend needs to infer backend truth
- LLM would need to decide completion/recording
- required typed event/state does not exist
- tests cannot be written because contract is unclear

## Reporting format
Report:
1. Files changed
2. Source-of-truth section used
3. Behavior implemented
4. Tests added/updated
5. Commands run and results
6. Remaining risks/blockers
