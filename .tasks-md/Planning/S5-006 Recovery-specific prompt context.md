# S5-006 Recovery-specific prompt/context

Status: Planning
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

- [ ] Recovery context builder created
- [ ] Recovery context includes: failed step, error, tried fixes
- [ ] No full planning/execution history
- [ ] Phase instruction includes recovery scope rules
- [ ] Context tokens reduced for recovery
- [ ] Telemetry includes context_mode="recovery_recent_evidence"
- [ ] Output schema unchanged

## Evidence

Will include:
- Recovery context builder implementation
- Unit test output showing focused context
- Contract test output showing scope instruction
- Integration test telemetry with context_level
- Token estimate comparison: baseline vs recovery context

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
