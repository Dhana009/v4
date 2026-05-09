# SPRINT-005 Planning Board

**Sprint:** Sprint 5 — Purpose-Specific LLM Runtime and Token Efficiency
**Status:** Planning
**Type:** Major build sprint (15 stories)

## Overview

Sprint 5 wires purpose-specific LLM policies into the live call path, implements compact prompt packs, and proves token efficiency through fake-model testing. Goal: every LLM call is measurable, policy-controlled, and optimized without reducing correctness.

**Theme:** Make the LLM runtime strong and efficient by being purpose-specific.

## Current state

- PURPOSE_REGISTRY (14 purposes) defined but not wired to live calls
- Deterministic fast path for simple clicks (0 tokens)
- Compact skills and context windows exist but not enforced
- Token baseline: 3496 system + 3398 skill dominant cost

**Gap:** Live agent.py calls bypass LLMRuntimeController. Policies exist but aren't applied.

## Story list

| ID | Title | Tier | Status | Blocks | Blocked by |
|---|---|---|---|---|---|
| S5-001 | Live LLM call path through LLMRuntimeController | 1 | Planning | S5-002, S5-005, S5-006, S5-010 | — |
| S5-002 | Purpose-specific prompt pack builder | 1 | Planning | S5-007 | S5-001 |
| S5-003 | Skill summary/full-skill escalation policy | 1 | Planning | — | — |
| S5-004 | Tool schema filtering by purpose | 1 | Planning | S5-009 | — |
| S5-005 | Context reuse and delta context for correction | 2 | Planning | — | S5-001 |
| S5-006 | Recovery-specific prompt/context | 2 | Planning | — | S5-001 |
| S5-007 | Token report attribution upgrade | 3 | Planning | S5-013 | S5-002 |
| S5-008 | ModelRouter real cheap/main routing contract | 3 | Planning | — | — |
| S5-009 | Page Intelligence LLM route design and contract | 4 | Planning | S5-010 | S5-004 |
| S5-010 | Page Intelligence first fake-model integration | 4 | Planning | S5-012 | S5-009 |
| S5-011 | DOM-heavy fixture pages for LLM-runtime testing | 4 | Planning | S5-012 | — |
| S5-012 | Fake-model integration suite for planning/correction/recovery | 4 | Planning | S5-013 | S5-010 |
| S5-013 | Controlled paid E2E acceptance for Sprint 5 | 5 | Planning | — | S5-001, S5-007, S5-012 |
| S5-014 | Prompt/cache-friendly stable prefix strategy | 5 | Planning | — | S5-002 |
| S5-015 | Sprint 5 regression guardrails | 5 | Planning | — | S5-001, S5-002, S5-003, S5-004 |

## Recommended first 3 stories

**Critical path:**

1. **S5-001** (Live LLM call path through LLMRuntimeController)
   - Unblocks everything
   - Implement wiring only, no behavior changes
   - Fake-model tests only (no paid LLM)

2. **S5-002** (Purpose-specific prompt pack builder)
   - Builds on S5-001 wiring
   - Prove system prompt reduction (3496 → 3000 tokens)
   - Direct impact on token cost

3. **S5-003** (Skill summary/full-skill escalation policy)
   - Independent of S5-001/002
   - Can run in parallel with S5-002
   - Prove skill loading policy (3398 → ~1500 tokens)

**Why:** S5-001 is critical path. S5-002 and S5-003 together target the dominant token buckets (system + skill = 6894 tokens). Once these three are done, the sprint has proven the core cost reduction hypothesis.

## Sprint rules

- **No paid LLM until S5-013.** All development uses fake model.
- **No code changes until tickets are approved.** Plan first, implement second.
- **Fake-model suite (S5-012) is non-negotiable.** Development depends on it.
- **Regression gates (S5-015) are last story but inform all others.** Define guardrails early.
- **Token measurement (S5-007) is required.** Every story must show telemetry.

## Success criteria

- [ ] S5-001 through S5-004 complete (core wiring and policies)
- [ ] Token reduction demonstrated: ≤110% of baseline (accept 10% variance)
- [ ] Correctness unchanged: all flows still pass
- [ ] Fake-model suite proves architecture works without paid LLM
- [ ] Controlled E2E (S5-013) validates real-LLM behavior
- [ ] Regression gates (S5-015) prevent future regressions

## Key milestones

| Milestone | Stories | Expected outcome |
|---|---|---|
| **Core wiring complete** | S5-001 through S5-004 | LLMRuntimeController active, policies enforced, tool filtering works |
| **Token baseline proven** | S5-001 through S5-007 | Token report shows prompt/skill/tool reduction vs baseline |
| **Page Intelligence ready** | S5-009 through S5-011 | DOM-heavy fixture pages, fake-model integration works |
| **Fake-model suite complete** | S5-012 | All core flows testable without paid LLM |
| **Sprint acceptance** | S5-013 through S5-015 | Controlled E2E shows <10% token variance, guardrails prevent regressions |

## Acceptance gates per tier

**Tier 1 (S5-001 through S5-004):**
- Live planning calls route through LLMRuntimeController
- Purpose-specific policies enforced (tools, skills, context)
- Token reduction measurable
- All 5 E2E flows still pass

**Tier 2 (S5-005, S5-006):**
- Context deltas working (correction, recovery)
- Token measurement shows reduced context per purpose
- No behavior change

**Tier 3 (S5-007, S5-008):**
- Telemetry reports exact cost attribution
- Model routing contract validated

**Tier 4 (S5-009 through S5-012):**
- Page Intelligence schema defined
- Fake-model suite covers planning/correction/recovery
- No paid calls needed for development

**Tier 5 (S5-013, S5-014, S5-015):**
- Controlled E2E shows feasibility with real LLM
- Cache-friendly prefix structure
- Regression gates in CI

## Notes

- This is a major build sprint, not a cleanup sprint
- Focus is LLM runtime strength and token efficiency, not UI polish
- Safety rules are non-negotiable; no context cuts that reduce correctness
- Token measurement is critical; every story must show telemetry impact
- Fake-model driven development keeps costs down during implementation
