# S5-002 Purpose-specific prompt pack builder

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, AGENTS.md token baseline, runtime/llm_runtime_controller.py

## Problem / Goal

**Problem:** All LLM calls receive the same heavy system prompt (~3496 tokens). This dominates per-call overhead.

**Goal:** Create compact prompt packs per purpose (stable prefix + minimal dynamic suffix). step_plan_normalizer pack should be ≤3000 tokens vs current ~3500.

## Scope

- Build prompt-pack builder module: `runtime/prompt_pack_builder.py`
- Implement step_plan_normalizer pack first (planning-specific rules only)
- Separate stable prefix (deterministic rules) from dynamic suffix (phase/context instructions)
- Preserve all safety rules and critical context
- Plan_diff_editor second if safe (pure plan-edit rules)

Out of scope:
- All 14 purpose packs at once — implement 2–3 as proof
- Removing safety rules or context required for correctness
- Changing output schema
- LLM behavior adaptation (packs are static templates)

## Required unit tests

- `test_prompt_pack_builder.py`:
  - build_step_plan_normalizer_pack() returns dict with prefix/suffix
  - prefix is stable and deterministic
  - suffix includes phase/context markers
  - total tokens ≤3000
  - all critical safety rules present
- `test_prompt_pack_tokens.py`:
  - Estimate tokens for each pack
  - Compare vs baseline (old system prompt)
  - Verify reduction

## Required contract tests

- `test_prompt_pack_safety_rules.py`:
  - Presence of: "LLM reasons but does not decide", "backend owns truth", "no recording without evidence"
  - All phase instructions intact
  - No silent behavior change

## Required integration tests

- `test_planning_with_compact_pack.py`:
  - LLMRuntimeController calls prompt-pack builder
  - Planning call uses compact pack instead of old system prompt
  - Telemetry includes prompt_pack_id

## Fixture/page needs

None.

## Paid E2E requirement

None — pack is template only.

## Acceptance criteria

- [ ] Prompt-pack builder module created and tested
- [ ] step_plan_normalizer pack is ≤3000 tokens (vs ~3500)
- [ ] Stable prefix hash is deterministic
- [ ] All critical safety rules present and unchanged
- [ ] Phase/context instructions are dynamic suffix
- [ ] Telemetry includes prompt_pack_id and prefix_hash
- [ ] No change in LLM output quality (verified in controlled E2E later)

## Evidence

Will include:
- `runtime/prompt_pack_builder.py` with builder functions
- Unit test passing output with token estimates
- Contract test output proving safety rules
- Integration test telemetry JSON sample showing prompt_pack_id
- Comparison table: old system prompt tokens vs new pack tokens

## Verification commands/results

```bash
pytest tests/test_prompt_pack_builder.py -v
pytest tests/test_prompt_pack_tokens.py -v
pytest tests/test_prompt_pack_safety_rules.py -v
pytest tests/test_planning_with_compact_pack.py -v

# Spot check: new pack should be 10–15% smaller than old system prompt
grep "system.*3496" AGENTS.md  # baseline reference
# vs new estimate in test output
```

## Risk

- **Medium:** Compact pack may omit context that real-LLM behaviors depend on
- **Low:** Prefix hash collision (acceptable with content-hash checksum)

## Mitigation

- Contract test explicitly checks for critical rules and instructions
- Controlled E2E (S5-013) compares output quality
- Safety-rule regression gate (S5-015)
