# SPRINT-005 Purpose-Specific LLM Runtime and Token Efficiency

Status: Planning
Sprint: Sprint 5
Duration: Bi-weekly / Major LLM-runtime build sprint
Type: Sprint
Priority: P0

## Goal

Wire purpose-specific LLM policies into the live call path, implement compact prompt packs per purpose, route multi-model decisions, and prove token efficiency without reducing correctness.

**Strategic outcome:** Every LLM call is purpose-specific, measurable, and policy-controlled. Token cost is visible and attributed to exact prompt pack, skill names, tool schema, and context buckets.

## Why Sprint 5 is needed

### Current state

The runtime layer has:
- PURPOSE_REGISTRY with 14 named purposes (defined in llm_runtime_controller.py)
- LLMPolicyGateway that classifies phases into purposes
- skill_policy.py with compact/full/debug skill loading rules
- ContextManager with purpose-specific compaction windows
- page_intelligence.py deterministic HTML summarization
- deterministic_fast_path for 0-token simple flows

**But:** The live LLM call path in agent.py does NOT route through LLMRuntimeController.call(). All calls still use main_orchestrator with the same heavy system prompt and skill payload.

### Token baseline (confirmed from Sprint 3 audit)

Current LLM-required flow uses:
- **system: 3,496 tokens** (dominant)
- **skill: 3,398 tokens** (dominant)
- tool_schema: 410 tokens
- history: 495 tokens
- DOM/tool: 4 tokens

**Key insight:** Dominant cost is system prompt + skill payload, not DOM size.

### What Sprint 5 changes

1. **Live call wiring:** Route planning/correction/recovery calls through LLMRuntimeController with actual purpose
2. **Prompt packs:** Create compact purpose-specific prompt packs (stable prefix + minimal dynamic suffix)
3. **Skill escalation:** Load compact skill summaries by default; full skill only on explicit escalation
4. **Tool filtering:** Stop sending all tool schemas; purpose limits tools by phase
5. **Context reuse:** Correction/recovery use delta context, not full planning history
6. **Model routing:** real cheap/main model class decisions (not just metadata)
7. **Page Intelligence:** Structured output contract for cheap DOM analysis
8. **Testing:** Fake-model suite so development doesn't rely on paid LLM
9. **Telemetry:** Token reports show exact prompt pack, skill names, skill levels, model class
10. **Guardrails:** Regression gates prevent future prompt/token/safety regressions

## Success criteria

### Functional

- [ ] S5-001: live planning calls route through LLMRuntimeController with purpose=step_plan_normalizer
- [ ] S5-002: step_plan_normalizer prompt pack is <=3000 tokens (vs current ~3500)
- [ ] S5-003: compact skill summaries load by default; full skill only on explicit escalation
- [ ] S5-004: planning calls expose only planning tools, correction calls expose no browser tools
- [ ] S5-005: plan_diff_editor uses delta context (plan+correction, no full history)
- [ ] S5-006: recovery uses recovery_recent_evidence context, not full history
- [ ] S5-007: token report shows purpose, prompt_pack_id, skill names, skill levels
- [ ] S5-008: model_router routes cheap/main purposes correctly
- [ ] S5-009: page intelligence output contract defined and tested
- [ ] S5-010: fake-model integration suite covers planning/correction/recovery without paid LLM
- [ ] S5-011: DOM-heavy fixture pages support testing
- [ ] S5-012: controlled paid E2E shows <10% token reduction vs baseline, same correctness

### Quality gates

- [ ] No safety rules removed to save tokens
- [ ] All 5 E2E flows still pass
- [ ] Backend-truth boundaries remain intact
- [ ] No LLM decision on completion/recording
- [ ] No browser action before confirmation
- [ ] Frontend renders backend truth only

## Sprint composition

15 stories, organized by implementation priority and dependency.

### Tier 1: Core wiring (S5-001 through S5-004)

Stories that wire the fundamental call path and apply basic policies.

**S5-001:** Live LLM call path through LLMRuntimeController
**S5-002:** Purpose-specific prompt pack builder
**S5-003:** Skill summary/full-skill escalation policy
**S5-004:** Tool schema filtering by purpose

### Tier 2: Context and recovery (S5-005, S5-006)

Stories that optimize context for specific purposes.

**S5-005:** Context reuse and delta context for correction
**S5-006:** Recovery-specific prompt/context

### Tier 3: Measurement and routing (S5-007, S5-008)

Stories that make changes measurable and route multi-model.

**S5-007:** Token report attribution upgrade
**S5-008:** ModelRouter real cheap/main routing contract

### Tier 4: Page Intelligence and testing (S5-009 through S5-012)

Stories that add cheap DOM analysis and prove it works without paid LLM.

**S5-009:** Page Intelligence LLM route design and contract
**S5-010:** Page Intelligence first fake-model integration
**S5-011:** DOM-heavy fixture pages for LLM-runtime testing
**S5-012:** Fake-model integration suite for planning/correction/recovery

### Tier 5: Acceptance and guardrails (S5-013, S5-014, S5-015)

Stories that verify Sprint 5 works and prevent regressions.

**S5-013:** Controlled paid E2E acceptance for Sprint 5
**S5-014:** Prompt/cache-friendly stable prefix strategy
**S5-015:** Sprint 5 regression guardrails

## Recommended execution order

1. **S5-001** (live controller wiring) — blocks everything
2. **S5-002** (prompt packs) — blocks telemetry
3. **S5-003** (skill escalation) — independent
4. **S5-004** (tool filtering) — independent
5. **S5-005** (correction context) — builds on S5-001
6. **S5-006** (recovery context) — builds on S5-001
7. **S5-007** (token attribution) — blocks E2E verification
8. **S5-008** (model routing) — independent
9. **S5-009** (page intelligence contract) — builds on S5-004
10. **S5-010** (fake-model integration) — builds on S5-009
11. **S5-011** (DOM-heavy fixtures) — independent
12. **S5-012** (fake-model suite) — builds on S5-010
13. **S5-013** (paid E2E) — builds on all above
14. **S5-014** (stable prefix) — builds on S5-002
15. **S5-015** (guardrails) — last, validates all above

## What NOT to do in Sprint 5

- [ ] Do NOT broad-refactor agent.py — focus only on LLMRuntimeController wiring
- [ ] Do NOT chase deterministic fast path optimization unless audit shows a new gap
- [ ] Do NOT remove safety rules to save tokens — correctness first
- [ ] Do NOT rely on frontend polish as success metric
- [ ] Do NOT implement nano/cheap model provider integration (defer to follow-up)
- [ ] Do NOT rewrite all skill files — use existing skill_policy.py rules
- [ ] Do NOT change output schemas unless required by purpose-specific needs
- [ ] Do NOT commit to paid E2E beyond controlled acceptance runs

## Key architectural principles

**Backend = runtime truth.** No LLM decides completion or recording.

**LLM = reasoning/proposal only.** All model outputs are validated by Step Runner before action.

**DOM/page intelligence = candidate provider.** Structured suggestions, not execution.

**Purpose-specific runtime.** Every call has explicit purpose, tools, skills, context policy, and telemetry.

**Measurable cost.** Token attribution by prompt-pack, purpose, skill names, skill levels, tool schema, context bucket.

**Quality before tokens.** No context omission that reduces correctness.

**Fake-model driven development.** Paid LLM only for final acceptance.

## Open questions before implementation

1. **Prompt pack versioning:** Should prompt_pack_id include version? How to evolve packs?
2. **Skill escalation trigger:** What exact conditions trigger full-skill escalation? Schema failure? Token budget exceeded?
3. **Cheap model fallback:** If page_intelligence returns malformed output, fallback to raw DOM or fail-closed?
4. **Correction scope:** Should plan_diff_editor allow target/locator changes without DOM extraction, or is DOM always required?
5. **Recovery context window:** How many failed steps back should recovery context preserve? Just last failed step or last N failures?
6. **Telemetry cardinality:** Is skill names array or comma-separated string? Should telemetry include prompt_pack_version?
7. **Fake model output:** What LLM response format should fake-model emit for planning/correction/recovery?
8. **Page Intelligence nano cost:** If cheap model is routed to real nano/smaller API, what cost estimate should inform token budgets?
9. **Prompt cache strategy:** Should stable prefix hash be deterministic per purpose/version for provider cache friendliness?
10. **Regression gate threshold:** What token% increase triggers CI failure? 10%? 5%?

---

## Related documents

- PRD v2.3: `/PRD_v2_3_Modular_Pack_v2/00_MASTER_INDEX.md`
- LLM Runtime spec: `/PRD_v2_3_Modular_Pack_v2/02_LLM_RUNTIME.md`
- Multi-Model Orchestration: `/PRD_v2_3_Modular_Pack_v2/07_MULTI_MODEL_ORCHESTRATION.md`
- Sprint 3 baseline: `/AGENTS.md` token cost section
- Runtime inventory: `runtime/llm_runtime_controller.py`, `runtime/llm_policy_gateway.py`, `runtime/skill_policy.py`, `runtime/context_manager.py`, `runtime/page_intelligence.py`

## Notes

- Sprint 5 is a major build sprint, not a cleanup sprint
- Token measurement is critical — every story must include telemetry verification
- Fake-model suite must be comprehensive enough that core flows are testable without paid calls
- All stories should fit within a bi-weekly sprint with clear done criteria
- Tier 1 stories are critical path; later tiers can be deferred if needed, but core wiring (S5-001 through S5-004) must complete
