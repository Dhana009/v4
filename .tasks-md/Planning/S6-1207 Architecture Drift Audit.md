# S6-1207: Architecture Drift Audit

## Objective

Ensure implementation did not violate non-negotiables.

## Acceptance Criteria

- [ ] No ad-hoc LLM calls outside controller
- [ ] No frontend lifecycle inference
- [ ] No trace-as-truth
- [ ] No raw full DOM by default
- [ ] No all-tools/all-skills calls
- [ ] No unvalidated locator activation
- [ ] No recording/code_update without backend evidence
- [ ] No replay mutation without validated repair
- [ ] No broad monolith growth (agent.py/server.py < 10%)
- [ ] Any drift is fixed or documented as blocker

## Architecture Invariants

1. LLM Call Centralization: All LLM calls through ControllerRuntime
2. Frontend Lifecycle Isolation: Frontend dispatches, backend owns lifecycle
3. Trace as Diagnostic: Trace mirrors events, not truth
4. Raw DOM Handling: DOM extracted/summarized, not full dump
5. Tool/Skill Exposure: Specific purpose → specific tools
6. Locator Validation: Validated before use
7. Recording/Code Update: Backend evidence required
8. Replay Safety: Read-only, no mutations

## Drift Categories

- **Category 1: Fix** - Ad-hoc LLM, trace mutation, unvalidated locators
- **Category 2: Document** - Minor growth, justified exceptions
- **Category 3: Block** - Requires architectural change

## Notes

Drift audit is the final sanity check. Non-negotiables prevent specific failures.
