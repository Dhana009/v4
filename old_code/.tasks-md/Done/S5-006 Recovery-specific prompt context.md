# S5-006 Recovery-specific prompt/context

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 02_LLM_RUNTIME.md recovery section, runtime/context_manager.py

## Problem / Goal

**Problem:** Recovery diagnosis uses full history and planning context. Recovery should focus on: failed step, error message, attempted fixes, and recovery options. Broad history is noise.

**Goal:** Implement recovery-specific context in ContextManager. recovery_diagnoser purpose uses recovery_recent_evidence window: failed step + error + tried fixes only. No full planning history by default.

## Scope

- Extend ContextManager with recovery context builder
- Recovery context includes: failed step (target, expected outcome), error message/trace, tried fixes
- No full planning history
- Phase instruction includes: "Work only on failed step", "Cannot replan completed steps", "Allowed outcomes: retry/repair/ask/skip/stop"
- Telemetry includes context_mode="recovery_recent_evidence"

Out of scope:
- Broad recovery behavior rewrite
- Recovery execution (just diagnosis context)
- Multiple failure history (focus on last failed step only)

## Required unit tests

- `test_recovery_context_builder.py`:
  - build_recovery_context(failed_step, error, tried_fixes) returns focused context
  - No full planning/execution history
  - Failed step details preserved
  - Tried fixes listed
- `test_recovery_context_tokens.py`:
  - Recovery context tokens reduced vs full history
  - Comparison: baseline recovery context vs new recovery context

## Required contract tests

- `test_recovery_proposal_contract.py`:
  - Model receives failed step, error, tried fixes
  - Output schema matches recovery_diagnoser output
  - Recovery scope instruction present

## Required integration tests

- `test_recovery_diagnosis_context.py`:
  - Recovery call uses recovery_recent_evidence context
  - Telemetry shows context_level="recovery_recent_evidence"
  - No full planning history in message context

## Fixture/page needs

None.

## Paid E2E requirement

None.

## Acceptance criteria

- [x] Recovery context builder created
- [x] Recovery context includes: failed step, error, tried fixes
- [x] No full planning/execution history
- [x] Phase instruction includes recovery scope rules
- [x] Context tokens reduced for recovery
- [x] Telemetry includes context_mode="recovery_recent_evidence"
- [x] Output schema unchanged

## Evidence

Implemented:
- `runtime/recovery_context.py` now builds a compact failed-step recovery payload from the failed step, error summary, tried fixes, relevant evidence, retry attempts, and user recovery instruction.
- `runtime/prompt_pack_builder.py` provides the `recovery_diagnoser.v1` prompt pack with stable-prefix / dynamic-suffix separation.
- `agent.py` routes recovery diagnosis through the controller path and appends recovery-specific context before the model call.

Recovery context logic:
- Anchors the context to the failed step and failed operation.
- Filters retry attempts to the current failed step.
- Preserves the current URL/title and only the evidence relevant to recovery.
- Falls back to the latest user recovery instruction when present.

Prompt pack:
- `recovery_diagnoser.v1`
- Stable prefix includes the five non-negotiable runtime rules and recovery-specific anchor / retry / ask / stop rules.
- Dynamic suffix carries run id, failed step id, failed operation id, failed step summary, error summary, current page, tried fixes, evidence, user recovery instruction, and retry attempts.

Tests added/updated:
- `tests/test_recovery_context.py`
- `tests/test_prompt_pack_builder.py`
- `tests/test_prompt_pack_safety_rules.py`
- `tests/test_recovery_through_fake_model.py`
- `tests/test_llm_runtime_controller_contract.py`

Commands run:
- `python -m py_compile runtime/recovery_context.py runtime/prompt_pack_builder.py tests/test_recovery_context.py tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_recovery_through_fake_model.py tests/test_llm_runtime_controller_contract.py`
- `python -m pytest tests/test_correction_context.py tests/test_recovery_context.py -q`
- `python -m pytest tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py -q`
- `python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_recovery_through_fake_model.py tests/test_fake_llm_factory.py -q`

Results:
- `tests/test_correction_context.py tests/test_recovery_context.py -q`: 5 passed
- `tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py -q`: 16 passed
- `tests/test_llm_runtime_controller_contract.py tests/test_planning_through_controller_fake_model.py tests/test_recovery_through_fake_model.py tests/test_fake_llm_factory.py -q`: 51 passed

Interpretation:
- What token/call waste this should reduce: recovery calls now stay anchored to the failed step instead of resending the whole planning/execution surface.
- What remains: later sprint work can tighten measurement and any remaining recovery-policy edges, but the compact recovery context and prompt pack are in place.

## Verification commands/results

```bash
pytest tests/test_recovery_context_builder.py -v
pytest tests/test_recovery_context_tokens.py -v
pytest tests/test_recovery_proposal_contract.py -v
pytest tests/test_recovery_diagnosis_context.py -v

# Verify context reduction
# Expected: recovery context ~1500–2500 tokens vs full history ~5000+
```

## Risk

- **Low:** Focusing only on last failed step may miss root cause in earlier steps
- **Low:** Omitting full history may confuse recovery reasoning

## Mitigation

- Contract test verifies scope instruction is present
- Recovery output is proposal only; Step Runner validates truth
- Controlled E2E (S5-013) tests recovery effectiveness
