# SPRINT-005-REMAINING-SCOPE-AUDIT

**Generated:** 2026-05-12
**HEAD commit:** a4d23f3df8dca28fb882ab7911e6e471b4f06910
**Branch:** main (27 commits ahead of origin/main)
**Status at audit:** S5-013 Done. S5-008, S5-009, S5-010, S5-011 remain in Planning.

---

## 1. Done Stories

| ID | Title | Evidence |
|----|-------|----------|
| S5-001 | Live LLM call path through LLMRuntimeController | agent.py routes step_plan_normalizer through controller |
| S5-001B | Controller raw-response tool-call preserving planning path | call_with_raw_response() preserves tool_calls |
| S5-002 | Purpose-specific prompt pack builder | runtime/prompt_pack_builder.py, step_plan_normalizer.v1 |
| S5-003 | Skill summary/full-skill escalation policy | runtime/skill_selector.py, skill_policy.py |
| S5-004 | Tool schema filtering by purpose | runtime/tool_schema_policy.py, 15→6 tools for planning |
| S5-005 | Context reuse and delta context for correction | runtime/prompt_packs.py correction context modes |
| S5-006 | Recovery-specific prompt context | runtime/prompt_packs.py recovery_recent_evidence |
| S5-007 | Token report attribution upgrade | 8 telemetry fields, 4 token report fields |
| S5-012 | Fake-model integration suite | test_planning_through_controller_fake_model.py |
| S5-013 | Controlled paid E2E acceptance | Passed 2026-05-12; ask_user observed; 2 LLM calls |
| S5-014 | Prompt cache-friendly stable prefix strategy | prefix_hash in telemetry, stable prefix confirmed |
| S5-015 | Sprint 5 regression guardrails | test_sprint5_paid_retry_blocker_regression.py |

**Total done: 12 of 15 stories.**

---

## 2. Remaining Stories

| ID | Title | Status | Tier | Blocked by |
|----|-------|--------|------|-----------|
| S5-008 | ModelRouter real cheap/main routing contract | Planning | 3 | — (independent) |
| S5-009 | Page Intelligence LLM route design and contract | Planning | 4 | S5-004 (Done) |
| S5-010 | Page Intelligence first fake-model integration | Planning | 4 | S5-009 |
| S5-011 | DOM-heavy fixture pages for LLM-runtime testing | Planning | 4 | — (independent) |

**Total remaining: 3 stories + 1 foundation story.**

Dependency order: S5-011 || S5-008 → S5-009 → S5-010

---

## 3. Open Bugs

**None.** All BUG-S5-013-001 through BUG-S5-013-012 are Done.

---

## 4. Stories No Longer Needed Due to S5-013 Work

None of the remaining stories (S5-008, S5-009, S5-010, S5-011) were made obsolete by S5-013 work.

S5-013 work (convergence narrowing, forced tool_choice, schema stripping) addressed runtime correctness for the existing single-model path. It did not implement:
- ModelRouter cheap/main routing (S5-008)
- Page Intelligence schema or fake integration (S5-009, S5-010)
- DOM fixture pages (S5-011)

All four remaining stories are still needed per original sprint scope.

---

## 5. Stories Still Requiring Implementation

### S5-008 — ModelRouter real cheap/main routing contract
**What:** Extend `runtime/model_router.py` to route `model_class="cheap"` → cheap model name, `model_class="main"` → main model name, with explicit fallback chain. Currently model_router is a passthrough; all LLM calls use one model regardless of purpose.

**Why still needed:** Multi-model routing is a sprint goal (PRD §7 MULTI_MODEL_ORCHESTRATION). Without it, page_intelligence cannot run on a cheaper model and the ModelRouter contract is unproven.

**Scope:** model_router.py only. No production key changes. Fake provider tests only.

---

### S5-011 — DOM-heavy fixture pages for LLM-runtime testing
**What:** Create 5–6 local HTML fixture pages in `tests/fixtures/pages/`: weak div/span page, duplicate CTA page, form-heavy page, docs/code-block page, modal/recovery page.

**Why still needed:** S5-009 and S5-010 (Page Intelligence) require weak/ambiguous pages for testing. The existing ambiguous-actions.html fixture serves convergence testing only. Purpose-specific page intelligence needs weak DOM pages with no semantic anchors.

**Scope:** tests/fixtures/pages/ HTML only. No runtime changes.

---

### S5-009 — Page Intelligence LLM route design and contract
**What:** Define `PageIntelligenceSchema` in `runtime/page_intelligence_schema.py`. Fields: page_or_section_summary, semantic_quality (good|mixed|poor), elements list (confidence/risk), ambiguities, risk_flags. Contract tests for schema validation and advisory-only boundary.

**Why still needed:** Page Intelligence purpose exists in PURPOSE_REGISTRY but has no structured output contract. Without a schema, fake-model integration (S5-010) cannot be written.

**Scope:** runtime/page_intelligence_schema.py (new), tests/test_page_intelligence_schema.py. No agent.py changes.

---

### S5-010 — Page Intelligence first fake-model integration
**What:** Wire page_intelligence_summarizer purpose through LLMRuntimeController. Weak DOM → fake model → PageIntelligencePacket → main planner receives summary, not raw DOM. Verify Step Runner still validates locator before action.

**Why still needed:** This is the payoff story for S5-009 + S5-011. Proves the multi-purpose architecture works end-to-end without paid LLM. Required for sprint success criteria §10.

**Scope:** runtime/page_intelligence.py (extend), agent.py (page intelligence trigger), tests/.

---

## 6. Recommended Next Cluster

**Cluster: S5-008 + S5-011 in parallel, then S5-009, then S5-010**

Execution order:
1. **S5-008** (ModelRouter routing) — independent, no fixtures needed, no paid LLM, ~1 day
2. **S5-011** (DOM fixture pages) — independent, pure HTML, enables S5-009+S5-010, ~0.5 day
3. **S5-009** (Page Intelligence schema + contract) — requires S5-011 for test fixtures
4. **S5-010** (Page Intelligence fake integration) — requires S5-009 schema

---

## 7. Why That Cluster Is Next

1. **S5-008 unblocks nothing but completes sprint goal §8** — ModelRouter routing contract is a standalone P1 story with no downstream blockers within this sprint. It is bounded, low risk, zero paid LLM.

2. **S5-011 is a pure prerequisite** — Without fixture pages, S5-009 has no weak DOM to write tests against. It must precede S5-009.

3. **S5-009 before S5-010** — Schema definition is the foundation. Fake integration without schema contract is building on sand.

4. **S5-010 is the sprint's final value story** — Proves multi-purpose LLM routing works end-to-end. Completes the Page Intelligence thread.

5. **No paid LLM needed for any of S5-008, S5-011, S5-009, S5-010** — All four use fake providers/fixtures only.

---

## 8. Allowed Files for Next Cluster

**S5-008:**
- `runtime/model_router.py` — extend routing logic
- `tests/test_model_router_routing_logic.py` — new
- `tests/test_model_router_config.py` — new
- `tests/test_model_router_contract.py` — new
- `tests/test_model_routing_with_fake_provider.py` — new

**S5-011:**
- `tests/fixtures/pages/*.html` — new fixture pages (5–6 files)
- `tests/test_fixture_pages_load.py` — new
- `tests/test_fixture_page_selectors.py` — new

**S5-009:**
- `runtime/page_intelligence_schema.py` — new
- `tests/test_page_intelligence_schema.py` — new
- `tests/test_page_intelligence_schema_validation.py` — new
- `tests/test_page_intelligence_output_contract.py` — new
- `tests/test_page_intelligence_advisory_boundary.py` — new

**S5-010:**
- `runtime/page_intelligence.py` — extend
- `agent.py` — page intelligence trigger (minimal)
- `tests/test_page_intelligence_summarizer_call.py` — new
- `tests/test_page_intelligence_flow.py` — new
- `tests/test_weak_dom_page_intelligence_flow.py` — new

---

## 9. Forbidden Files for Next Cluster

- `tests/e2e/` — no paid E2E for any of these stories
- `runtime/llm_runtime_controller.py` — already correct; do not touch
- `runtime/tool_registry.py` — convergence narrowing done; do not touch
- `runtime/prompt_pack_builder.py` — S5-002 done; do not touch
- `runtime/skill_selector.py` — S5-003 done; do not touch
- `runtime/tool_schema_policy.py` — S5-004 done; do not touch
- `tests/test_planning_convergence_contract.py` — S5-013 done; do not touch
- `.tasks-md/Done/` — read-only; do not move or edit closed stories

---

## 10. Test Plan for Next Cluster

### S5-008 tests (all fake provider, no real API)
- Route cheap model class → cheap model name (assert exact string)
- Route main model class → main model name (assert exact string)
- Fallback chain explicit + logged when cheap unavailable
- No fallback to expensive model for cheap purposes (fail-closed)
- Config accepts model_class map at init
- Telemetry includes model_class in router result

### S5-011 tests (static HTML, Playwright or requests)
- All 5–6 pages load without HTTP error
- Weak page has no role/aria-label/data-testid on CTAs
- Duplicate CTA page has identical visible text on 2+ buttons
- Form page has 3+ input fields
- Modal page can show/hide overlay
- Selector stability: same element found on 3 consecutive loads

### S5-009 tests (schema validation only, no model calls)
- Valid PageIntelligencePacket passes schema
- Missing semantic_quality → ValidationError
- Invalid semantic_quality value → ValidationError
- elements list missing confidence → ValidationError
- risk_flags and ambiguities are optional (absent = valid)
- Advisory boundary: schema has no action/execute fields

### S5-010 tests (fake model only)
- page_intelligence_summarizer purpose routes through LLMRuntimeController
- Fake model receives weak DOM excerpt in messages
- Returns valid PageIntelligencePacket
- Main planner messages include page summary, not raw DOM
- Summary token count < raw DOM token count
- Step Runner validates locator before action (integration guard)

---

## 11. Paid E2E Needed?

**No.** S5-008, S5-009, S5-010, S5-011 are all fake-model stories. No real LLM calls required.

Paid E2E (S5-013) is already Done. The next paid run would only be needed if:
- S5-010 fake integration passes and a real cheap model integration is wired (Sprint 6 scope)
- A regression is found that fake tests cannot reproduce

For the current cluster, paid E2E is **explicitly forbidden** per sprint rules: "No paid LLM until S5-013."

---

## Risks

1. **S5-009 schema design** — PageIntelligenceSchema must be rich enough for S5-010 fake integration but not over-engineered. Risk: schema too complex → S5-010 fake tests hard to write. Mitigation: keep advisory-only, 5-6 fields max.

2. **S5-010 agent.py trigger** — Adding page intelligence trigger to agent.py risks touching convergence narrowing logic. Mitigation: add a dedicated code path; no changes to `_step_plan_convergence_narrowing` flag or planning loop.

3. **S5-008 ModelRouter scope** — Current model_router.py is a thin passthrough. Extending it must not break the `main_orchestrator` path that currently bypasses it. Mitigation: treat existing behavior as the fallback case; new routing is additive.

4. **Fixture page quality** — Weak pages that are too simple won't exercise page intelligence realistically. Mitigation: base weak page on real-world pattern (e.g., CMS-generated div soup with no semantic attrs).
