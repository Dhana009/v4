# S5-003 Skill summary/full-skill escalation policy

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, runtime/skill_policy.py

## Problem / Goal

**Problem:** Skill loading is not systematic. Full skill files are loaded for all purposes equally (~3398 tokens per call). skill_policy.py defines levels but is not enforced in live calls.

**Goal:** Make light skill loading systematic. Load compact skill summaries by default. Full skill only on explicit escalation (schema failure, context required). Track loaded skill names and levels in telemetry.

## Scope

- Enforce skill_policy.py SKILL_LEVEL_MAP in live calls
- Build skill selector: `runtime/skill_selector.py`
- Load only required skills for each purpose
- Implement escalation logic: schema failure → load full skill
- Record skill names and levels in telemetry
- Preserve COMPACT_ONLY_PURPOSES enforcement (plan_diff_editor cannot load full skills)

Out of scope:
- Rewriting all skill files or creating new summaries (use existing SKILL_LEVEL_MAP)
- Changing skill content — only which skills load

## Required unit tests

- `test_skill_selector.py`:
  - select_skills_for_purpose(purpose="step_plan_normalizer") returns compact summaries
  - COMPACT_ONLY_PURPOSES cannot load full skills
  - escalation=True allows full skill loading
  - skill names match SKILL_LEVEL_MAP
- `test_skill_loading_policy_enforcement.py`:
  - correct skill level returned for each skill
  - escalation conditions trigger full skill

## Required contract tests

- `test_skill_escalation_contract.py`:
  - Schema validation failure → skill escalation attempt
  - Escalated call includes full skill content
  - Escalation is explicit in telemetry

## Required integration tests

- `test_planning_with_skill_summary.py`:
  - Planning call uses compact skill summary
  - Telemetry includes skills_loaded and skill_level
  - Skill tokens reduced vs baseline

## Fixture/page needs

None.

## Paid E2E requirement

None.

## Acceptance criteria

- [ ] skill_policy.py rules enforced in live call path
- [ ] Compact skill summaries loaded by default
- [ ] Full skill only on explicit escalation
- [ ] COMPACT_ONLY_PURPOSES cannot load full skills (plan_diff_editor, etc.)
- [ ] Telemetry includes: skills_loaded (list), skill_count, skill_levels
- [ ] Skill token bucket reduced vs baseline
- [ ] Escalation is logged and reported

## Evidence

Will include:
- `runtime/skill_selector.py` module
- Unit test output with skill level assertions
- Contract test output showing escalation path
- Integration test telemetry JSON with skills_loaded array
- Token estimate comparison: skill tokens in baseline vs S5-003

## Verification commands/results

```bash
pytest tests/test_skill_selector.py -v
pytest tests/test_skill_loading_policy_enforcement.py -v
pytest tests/test_skill_escalation_contract.py -v
pytest tests/test_planning_with_skill_summary.py -v

# Verify compact-only purposes
grep -E "COMPACT_ONLY_PURPOSES|plan_diff_editor" tests/test_skill_loading_policy_enforcement.py
```

## Risk

- **Low:** Compact skill summary missing context that real-LLM relies on (caught in E2E)
- **Low:** Escalation logic may trigger too often or not often enough

## Mitigation

- Controlled E2E (S5-013) measures quality
- Escalation conditions explicit and tested
- Fallback to full skill is safe but logged
