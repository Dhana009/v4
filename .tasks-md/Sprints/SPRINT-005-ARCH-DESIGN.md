# SPRINT-005-ARCH-DESIGN

AutoWorkbench Sprint 5 Architecture Design Report  
Produced: 2026-05-10  
Status: For review — do not begin implementation until approved

---

## 1. Executive Decision

### Recommended first 5 stories (in order)

| # | Story | Rationale |
|---|---|---|
| 1 | **S5-012** Fake-model integration suite | Foundation for all development. No paid LLM should be needed for any story. Must exist first so all other stories can be verified cheaply. A thin FakeLLM already exists in the test suite — extend it. |
| 2 | **S5-007** Token report attribution upgrade | Measurement-first. Without per-call attribution (prompt_pack_id, skill_names, tool_schema_tokens, context_bucket) you cannot prove that S5-001, S5-002, S5-003, S5-004 actually reduced anything. Build the gauge before tuning the engine. |
| 3 | **S5-001** Live LLM call path through LLMRuntimeController | The single gap that blocks all policy enforcement. plan_diff_editor already goes through the controller. The main planning loop does not. This story closes that gap for step_plan_normalizer, making the policy wiring real for the most costly call. |
| 4 | **S5-003** Skill summary/full-skill escalation policy | Skill payload (3,398 tokens) is the second-largest cost bucket and fully independent of the controller wiring. Can be implemented against existing skill_policy.py SKILL_LEVEL_MAP without any agent.py changes. |
| 5 | **S5-004** Tool schema filtering by purpose | Tool schema (410 tokens per call) is independent of prompt packs and can be reduced immediately once the controller is wiring tools. Particularly large win for plan_diff_editor (zero tools needed) and recovery (2 tools). |

### Stories to delay

| Story | Reason |
|---|---|
| S5-002 Prompt pack builder | Do not build prompt packs before the wiring exists (S5-001). Building packs without wiring is dead code. |
| S5-005 Delta context for correction | plan_diff_editor already uses the controller. Context optimization comes after measurement (S5-007). |
| S5-006 Recovery-specific context | Same reasoning — optimize after measure. |
| S5-008 ModelRouter cheap/main routing | No cheap model is available or configured. This is a design exercise until a real endpoint exists. Build the contract but do not block on it. |
| S5-009/S5-010 Page Intelligence | Requires fixture pages (S5-011) and fake-model integration (S5-012). Do after those exist. |
| S5-011 DOM fixture pages | Needed for S5-009/S5-010. Do in parallel with S5-003/S5-004 once S5-012 exists. |
| S5-013 Controlled paid E2E | Last. Only run after all wiring and reduction stories are complete. |
| S5-014 Stable prefix strategy | Useful but lowest cost-to-benefit. Prompt packs must exist first. Delay until S5-002 is done. |
| S5-015 Regression guardrails | Last gate. Implement after all policy changes are settled, not before. |

### Why this order vs the original

The original S5-001-first order is tempting but has three problems:
1. There is no measurement — you cannot prove it worked without S5-007.
2. There is no cheap test harness — every verification requires paid E2E or manual inspection.
3. The skill/tool cost is independent of wiring — S5-003 and S5-004 can run in parallel once S5-012 exists.

**Revised order:** measure first (S5-007), test harness first (S5-012), then wire (S5-001), then optimize independently (S5-003, S5-004).

---

## 2. Current Architecture Reality

### What exists and works

- `PURPOSE_REGISTRY`: 14 purposes fully defined in `runtime/llm_runtime_controller.py`, each with model_class, skill_policy, context_policy, tool_policy, output_schema, retry_policy, telemetry_fields.
- `LLMPolicyGateway`: classifies phase → purpose correctly. planning → step_plan_normalizer, correction → plan_diff_editor, recovery → recovery_diagnoser.
- `LLMRuntimeController.call()`: a complete async controller with context preparation, skill analysis, tool filtering, schema validation, retry, and telemetry emission. Already wired for plan_diff_editor.
- `ContextManager`: purpose-specific compact window policies for 4 purposes (step_plan_normalizer, plan_diff_editor, locator_specialist, recovery_diagnoser). DOM cap at 800 tokens. History compaction above 6,000 tokens.
- `skill_policy.py`: SKILL_LEVEL_MAP, COMPACT_ONLY_PURPOSES, LOCATOR_SUMMARY_PURPOSES, DEBUG_SKILL_PURPOSES defined. Not yet enforced live.
- `page_intelligence.py`: deterministic HTML → PageIntelligencePacket. No LLM. Already used.
- `deterministic_fast_path` + gateway: simple click/fill/assert bypass LLM entirely. Working in production.
- `ModelCallTelemetry`: records system_prompt_tokens, skill_tokens, tool_schema_tokens, message_history_tokens, dom_or_tool_result_tokens per call. Already working.
- `model_router.py`: passthrough. Receives purpose, logs it, calls client.chat.completions.create. No routing logic.
- FakeLLM patterns: test_model_router.py and test_llm_runtime_controller_contract.py show existing fake client patterns using SimpleNamespace.

### What is scaffolded but not wired

- **Controller call for planning**: The main loop in agent.py calls `self.model_router.call()` directly with `effective_purpose` in the metadata. It does NOT call `self._plan_diff_editor_controller.call()` or any controller equivalent for planning. The purpose is passed as a label only.
- **Skill loading enforcement**: `skill_policy.py` is imported but `should_load_full_skill()` is never called before a live LLM call to filter what gets sent.
- **Tool schema filtering via controller**: `LLMRuntimeController._filter_tools_for_phase()` exists and works, but the main loop uses `filter_tools_for_phase()` from `runtime/tool_registry.py` independently, not the controller.
- **Model routing by model_class**: `model_class` is in PURPOSE_REGISTRY metadata. `ModelRouter` ignores it — always routes to the single configured model.
- **prompt_pack_id / prefix_hash**: Not in ModelCallTelemetry. Not in token_report.py.

### What is missing entirely

- Prompt pack builder (`runtime/prompt_pack_builder.py`): does not exist.
- Per-purpose compact system prompts: currently one global system prompt for all calls.
- Skill escalation logic: no mechanism to detect schema failure → escalate to full skill.
- Delta context builder for correction: plan_diff_editor goes through the controller but still receives the full correction context injected before the call in `_run_plan_diff_editor_correction`.
- Page Intelligence cheap-model path: page_intelligence.py is deterministic only; no LLM path exists.
- DOM-heavy fixture pages: tests/fixtures/pages/ does not exist.
- Regression gates: no CI-gated budget or tool-policy assertions.

---

## 3. PRD Constraints

### Non-negotiables (from PRD v2.3 00_MASTER_INDEX.md)

- Backend Step Runner owns lifecycle, finality, recording, and replay truth.
- LLM reasons, decomposes, plans, explains, and repairs. It does not decide whether work is complete.
- Frontend must not infer lifecycle state from LLM text.
- Token optimization must never reduce correctness.
- No browser action before confirmation.
- No recording without backend evidence.

### LLM runtime requirements (from 02_LLM_RUNTIME.md)

- Plan correction is an intent-change event, not raw chat history.
- Active plan must be kept as an authoritative object (not only in LLM message history).
- Correction pipeline A (pure plan edit): no DOM extraction, no locator search.
- Correction pipeline B (target/locator edit): use locator_find/validate for changed target only.
- Correction pipeline C (expected outcome edit): action unchanged, expected result changes.
- Corrections must not silently drop, reorder, split, or merge unless user asked.

### Multi-model requirements (from 07_MULTI_MODEL_ORCHESTRATION.md)

- Sub-agents (cheap/nano models) do not execute Playwright actions, record steps, or decide finality.
- Sub-agent outputs are structured suggestions; Step Runner validates truth.
- Optional agent failures must degrade gracefully to deterministic extraction and/or main model.
- When an agent runs, UI must show which agent, why it ran, and what it produced.
- Every model call must log model, purpose, input/output tokens, estimated cost, and latency.
- Users must be able to turn non-essential agents on/off.
- Deterministic first when reliable — do not call a model if a deterministic rule can solve the task.

### Backend/event requirements (from 04_BACKEND_EVENT_CONTRACT.md)

- All events are typed WebSocket messages, not LLM-generated prose.
- plan_ready, plan_confirmed, step_recorded, code_update — all backend-emitted.
- LLM output is validated by schema validator before it influences backend state.
- Correction output → validated diff → backend applies → emits new plan_ready.

---

## 4. API Research Findings

### Prompt caching

**OpenAI (gpt-4o, gpt-4o-mini):**
- Automatic. No code changes required.
- Cache hits on identical prefixes ≥1,024 tokens, in 128-token increments.
- Cache lifetime: 5–10 minutes standard, up to 24 hours extended.
- **Implication for Sprint 5:** Stable prefix must be identical byte-for-byte across calls to same purpose. Dynamic context (plan, correction text, page data) must be in the suffix. This is the strongest design argument for separating stable prefix from dynamic suffix in prompt packs.

**Anthropic (claude-haiku-4-5 / sonnet-4-6):**
- Requires explicit `cache_control: {type: "ephemeral"}` on message blocks.
- Minimum: 1,024 tokens (Sonnet) or 4,096 tokens (Haiku/Opus).
- Cache write cost: ~125% of normal input tokens. Cache read cost: ~10%.
- **Implication:** System prompt (3,496 tokens) is large enough to benefit from Anthropic caching on Sonnet. But current system uses OpenAI client (`chat.completions.create`). Caching strategy must match the actual provider in use.

### previous_response_id / conversation state

**OpenAI Chat Completions API:** No built-in stateful conversation ID. `previous_response_id` is a feature of the Responses API only, which this codebase does not use.

**Implication for AutoWorkbench:** The current pattern (re-sending full message history with each call, managed client-side by agent.py) is the only correct approach for Chat Completions. ContextManager's compaction and windowing is therefore the right place to control cost. There is no server-side shortcut.

**Do NOT use Responses API or previous_response_id.** It would break the backend-as-truth principle: if the provider maintains conversation state, AutoWorkbench loses the ability to precisely control what context the model sees. This is a safety boundary, not a preference.

### Tool schema token cost

- Tool definitions are billed as input tokens.
- Filtering tools per call is a direct and reliable cost reduction.
- Current 410 tokens per call = all tools sent every call. For plan_diff_editor (zero tools needed), this is pure waste.
- **Verified: S5-004 tool filtering has highest ROI per implementation complexity.**

### Recommended provider strategy

1. **Keep Chat Completions API.** Do not migrate to Responses API. Backend-truth principle requires full control of context.
2. **Structure prompt packs with stable prefix first** to benefit from OpenAI's automatic prompt caching (≥1,024 token prefix, identical across calls to same purpose/version).
3. **Do not use cache_control flags unless migrating to Anthropic SDK.** Current code uses OpenAI client.
4. **Instrument cached_tokens from usage object** when available (`usage.prompt_tokens_details.cached_tokens` in OpenAI response). Add this field to ModelCallTelemetry in S5-007.

---

## 5. Recommended Sprint 5 Execution Order

| Order | Story | Why first/next | Required tests before implementation | Paid E2E? |
|---|---|---|---|---|
| 1 | **S5-012** Fake-model suite (core flows) | All development depends on fake-model testing. No paid LLM for any other story. Existing FakeLLM patterns in test_model_router.py and test_llm_runtime_controller_contract.py provide the scaffold. Extend to cover planning/correction/recovery schemas. | Existing controller contract tests pass. FakeLLM patterns reviewed. | No |
| 2 | **S5-007** Token report attribution | Measurement-first. Must show prompt_pack_id (even if null), skill_names, cached_tokens, tool_schema_tokens, context_bucket before any optimization. Creates the comparison baseline. | Unit tests for extended telemetry fields. Schema contract tests for token_report.json. | No |
| 3 | **S5-001** Live controller wiring (planning) | Closes the primary architectural gap. After S5-012 exists, wiring can be verified cheaply. After S5-007 exists, token impact is immediately measurable. Scope: step_plan_normalizer path only. plan_diff_editor already wired. | FakeLLM integration tests (S5-012). Token report showing purpose=step_plan_normalizer (S5-007). Existing controller contract tests pass. | No |
| 4 | **S5-003** Skill escalation policy | Independent of wiring. Can target the 3,398 token skill bucket immediately. Enforce existing SKILL_LEVEL_MAP in live calls. | Skill selector unit tests. Escalation contract tests. S5-007 token report showing skill_tokens reduction. | No |
| 5 | **S5-004** Tool schema filtering | Independent of prompt packs. Target 410 token overhead. plan_diff_editor wins most (zero tools). | Tool policy contract tests. S5-007 token report showing tool_schema_tokens reduction. | No |
| 6 | **S5-002** Prompt pack builder | After wiring (S5-001) and measurement (S5-007) exist. Build step_plan_normalizer pack first. Target the 3,496 token system bucket. Must preserve all safety rules — regression gate (S5-015) verifies. | Prompt pack unit tests. Safety rule contract tests. S5-007 token report showing system bucket reduction. | No |
| 7 | **S5-005** Delta context for correction | After S5-001 wiring proves the controller path. plan_diff_editor already uses controller — this story optimizes what goes into that call. | Context manager delta tests. Correction context token tests. | No |
| 8 | **S5-006** Recovery-specific context | Same reasoning. Recovery uses controller-routed purpose. Optimize context after wiring confirmed. | Recovery context unit tests. recovery_recent_evidence window tests. | No |
| 9 | **S5-008** ModelRouter cheap/main routing | Contract-only. No live cheap model yet. Define routing interface and fallback, test with fake provider. | Router unit tests. Fake provider contract tests. | No |
| 10 | **S5-011** DOM fixture pages | Required for S5-009/S5-010. Independent HTML pages, no LLM. | Fixture smoke tests. Selector stability tests. | No |
| 11 | **S5-009** Page Intelligence contract | Depends on S5-011 fixture pages. Define structured output schema. Test with fake model. | Schema contract tests. Advisory-boundary tests. | No |
| 12 | **S5-010** Page Intelligence fake-model integration | Depends on S5-009. Prove weak-DOM flow works end-to-end without paid LLM. | Fake-model integration tests. Backend validation boundary tests. | No |
| 13 | **S5-014** Stable prefix strategy | After S5-002 prompt packs exist. Separate stable prefix and dynamic suffix. Add prefix_hash to telemetry. | Hash determinism tests. Cache-friendliness contract. | No |
| 14 | **S5-015** Regression guardrails | After all policy changes are settled. CI-gated budget assertions, safety rule checks, tool policy checks. | All guardrail unit tests. False-positive-free CI run. | No |
| 15 | **S5-013** Controlled paid E2E | Last. Only after all wiring, optimization, fake-model suite, and guardrails are in place. Compare token counts against AGENTS.md baseline. | S5-007 baseline report. All fake-model integration tests passing. | **YES** (controlled, pre-approved, ≤3 flows) |

---

## 6. Foundational Test Plan

### Before any code changes, verify these pass

```bash
pytest tests/test_llm_runtime_controller_contract.py -v   # controller contracts intact
pytest tests/test_llm_policy_gateway.py -v                # gateway routing intact
pytest tests/test_context_manager.py -v                   # context manager intact
pytest tests/test_telemetry_breakdown.py -v               # telemetry fields intact
pytest tests/test_token_report.py -v                      # token report intact
pytest tests/test_model_router.py -v                      # model router intact
pytest tests/ -v --tb=short -q                            # full suite: 604 tests passing
```

### Unit tests needed (before implementation)

| Test file | Purpose | Unblocks |
|---|---|---|
| `tests/test_fake_llm_factory.py` | FakeLLM factory for planning/correction/recovery schemas | All fake-model stories |
| `tests/test_telemetry_extended_fields.py` | prompt_pack_id, cached_tokens, skill_names in ModelCallTelemetry | S5-007 |
| `tests/test_token_report_attribution.py` | token_report.json breakdown by purpose/skill/tool | S5-007 |
| `tests/test_skill_selector.py` | select_skills_for_purpose returns correct level | S5-003 |
| `tests/test_tool_schema_filter.py` | filter_tools_for_purpose returns correct subset | S5-004 |
| `tests/test_prompt_pack_builder.py` | build_step_plan_normalizer_pack token estimate and structure | S5-002 |
| `tests/test_prefix_hash_determinism.py` | same purpose → same prefix_hash | S5-014 |

### Contract tests needed

| Test file | Contract tested | Unblocks |
|---|---|---|
| `tests/test_controller_planning_call_contract.py` | planning call invokes controller with purpose=step_plan_normalizer | S5-001 |
| `tests/test_skill_escalation_contract.py` | COMPACT_ONLY_PURPOSES cannot load full skills | S5-003 |
| `tests/test_tool_policy_contract.py` | forbidden tools absent from schema by purpose | S5-004 |
| `tests/test_prompt_pack_safety_rules.py` | all critical safety rules present in every pack | S5-002/S5-015 |
| `tests/test_page_intelligence_advisory_boundary.py` | page intelligence output cannot execute or record | S5-009 |
| `tests/test_correction_diff_contract.py` | plan_diff_editor receives active plan + correction only | S5-005 |
| `tests/test_recovery_proposal_contract.py` | recovery_diagnoser receives failed step + error + tried fixes | S5-006 |

### Integration tests needed

| Test file | What it tests | Unblocks |
|---|---|---|
| `tests/test_planning_through_controller_fake_model.py` | planning end-to-end with FakeLLM, no real LLM | S5-001 |
| `tests/test_correction_through_fake_model.py` | correction end-to-end with FakeLLM | S5-005 |
| `tests/test_recovery_through_fake_model.py` | recovery end-to-end with FakeLLM | S5-006 |
| `tests/test_planning_token_attribution.py` | planning call generates attributed token report | S5-007 |
| `tests/test_weak_dom_page_intelligence_flow.py` | weak DOM → fake page intelligence → main planner | S5-010 |

### Fake-model patterns to establish

```python
# Standard FakeLLM pattern (extend from existing test_model_router.py)
class FakeLLMClient:
    def __init__(self, purpose_responses: dict[str, dict]) -> None:
        self.calls: list[dict] = []
        self.purpose_responses = purpose_responses
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **payload) -> Any:
        # Inspect last user message to find purpose
        # Return pre-configured schema-valid response for that purpose
        self.calls.append(payload)
        purpose = self._infer_purpose(payload)
        response_data = self.purpose_responses.get(purpose, self._default_response())
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(response_data),
                tool_calls=None,
            ))],
            usage=SimpleNamespace(
                prompt_tokens=100,
                completion_tokens=20,
                total_tokens=120,
                prompt_tokens_details=SimpleNamespace(cached_tokens=0),
            ),
        )
```

Fake responses needed per purpose:
- `step_plan_normalizer`: valid `plan_ready` JSON with one step, one child operation
- `plan_diff_editor`: valid corrected plan JSON
- `recovery_diagnoser`: valid recovery proposal JSON (retry or ask)
- `page_intelligence_summarizer`: valid PageIntelligenceSchema JSON
- `locator_specialist`: valid locator candidate JSON

### Telemetry fields to add (S5-007 scope)

```python
@dataclass
class ModelCallTelemetry:
    # ... existing fields ...
    prompt_pack_id: str | None = None          # NEW: which pack was used
    prompt_pack_version: int | None = None     # NEW: pack version
    skills_loaded: list[str] | None = None     # NEW: skill names (not just count)
    skill_levels: list[str] | None = None      # NEW: compact/full/debug per skill
    model_class: str | None = None             # NEW: cheap | main
    context_bucket: str | None = None          # NEW: planning|correction|recovery|other
    cached_tokens: int | None = None           # NEW: from usage.prompt_tokens_details
    prefix_hash: str | None = None             # NEW: stable prefix hash (S5-014)
```

### Fixture/page needs

```
tests/fixtures/pages/
├── weak_div_span_page.html       # No role/aria/testid CTAs
├── duplicate_cta_page.html       # Multiple identical "Next" buttons
├── form_heavy_page.html          # Login + signup + multi-step
├── docs_code_block_page.html     # Markdown-style, copy buttons
└── modal_recovery_page.html      # Modal overlays, dynamic state
```

### Controlled paid E2E (S5-013)

- Pre-approved only. Never during development.
- 2 flows max for Sprint 5 acceptance:
  1. Ambiguous intent → step_plan_normalizer → correction → confirmation (~5–8k tokens)
  2. DOM-heavy page intelligence flow if S5-010 is complete (~8–12k tokens)
- Acceptance: ≤110% of AGENTS.md baseline token count, same correctness.
- Cost estimate: $0.30–0.60 per run. Confirm before executing.

---

## 7. Purpose-Specific LLM Call Design

| Purpose | Model class | Prompt pack | Skills | Tools | Dynamic context | Output schema | Budget | Fallback |
|---|---|---|---|---|---|---|---|---|
| **step_plan_normalizer** | main | planning_pack_v1 | persona_compact | dom_extract, locator_find, locator_validate, send_to_overlay, ask_user | user intent, active page intelligence, current steps | plan_ready.v1 (steps + children) | 2,000 | main_orchestrator |
| **plan_diff_editor** | main | correction_pack_v1 | persona_compact only | none | active plan JSON, correction text, edit rules (no DOM unless target change) | corrected_plan.v1 | 2,200 | fail_closed |
| **recovery_diagnoser** | main | recovery_pack_v1 | persona_compact + debug_compact | browser_get_state, ask_user | failed step, error message, tried fixes (no full history) | recovery_proposal.v1 | 1,800 | ask_user |
| **locator_specialist** | main | locator_pack_v1 | locator_strategy_compact | dom_extract, locator_find, locator_validate | selected element context, page intelligence summary | locator_candidates.v1 | 2,200 | fallback_to_main |
| **page_intelligence_summarizer** | cheap | page_intel_pack_v1 | locator_strategy_compact | dom_extract (read-only) | raw cleaned DOM of selected section (capped 2000 chars) | PageIntelligenceSchema.v1 | 1,400 | deterministic_fallback |
| **replay_repair_specialist** | main | replay_pack_v1 | persona_compact + replay_compact | browser_get_state, ask_user | failed recorded operation, prior locator, last working state | repair_proposal.v1 | 1,800 | ask_user |
| **codegen_review** | main | codegen_pack_v1 | codegen_compact | none | generated TypeScript code, step spec, risk flags | review_result.v1 (pass/annotated) | 2,000 | auto_pass |

### Safety rules that must be in EVERY prompt pack

These are non-negotiable and must never be omitted for token savings:

```
1. "You reason and propose only. You do not decide step completion or recording."
2. "Backend Step Runner owns lifecycle truth. Your output is a proposal."
3. "No browser action executes before user confirmation."
4. "You may not instruct the frontend to record steps or update lifecycle state."
5. "Do not change the active plan structure silently. Every change must be explicit."
```

### Rules that can be purpose-specific (in dynamic suffix only)

- Phase instructions (planning vs correction vs recovery)
- Allowed tool list
- Schema format instructions
- Active plan context
- DOM / page intelligence
- Retry/fallback instructions

---

## 8. Recommended First Implementation Slice

### Start with: S5-012 + S5-007 in parallel, then S5-001

**First slice (can be done in one session):**

**A. S5-007 telemetry extension**

- Extend `ModelCallTelemetry` with: `prompt_pack_id`, `skills_loaded` (list), `skill_levels` (list), `model_class`, `context_bucket`, `cached_tokens`
- Extend `record_model_call_start()` to accept and store these fields
- Extend `token_report.py` to emit them in JSON breakdown
- Update existing `test_telemetry_breakdown.py` to cover new fields
- No behavior change, additive only

Allowed files: `runtime/telemetry.py`, `runtime/token_report.py`, `tests/test_telemetry_breakdown.py`, `tests/test_token_report.py`

Forbidden: `agent.py`, any runtime/ behavior files, tests/e2e/

Stop conditions:
- Any existing test breaks → revert and investigate
- New fields require non-additive schema changes → defer

**B. S5-012 FakeLLM factory**

- Create `tests/fake_llm_factory.py` (not a test file, a shared fixture)
- Implement `FakeLLMClient(purpose_responses={...})`
- Provide schema-valid stub responses for: step_plan_normalizer, plan_diff_editor, recovery_diagnoser
- Add `tests/test_fake_llm_factory.py` to verify stub outputs match PURPOSE_REGISTRY schemas

Allowed files: `tests/fake_llm_factory.py` (new), `tests/test_fake_llm_factory.py` (new)

Forbidden: any runtime/ file, agent.py

Stop conditions:
- Stub response schema doesn't match controller's expected output → design output schemas first
- FakeLLM requires changes to runtime/ to work → find seam in existing test patterns instead

**Second slice (after telemetry and fake-model confirmed):**

**S5-001 controller wiring**

- In agent.py main loop: after `policy_decision = self.llm_policy_gateway.decide(...)`, if `policy_decision.purpose == "step_plan_normalizer"`, route through a new `_plan_normalizer_controller` (same pattern as `_plan_diff_editor_controller`)
- Controller receives: client, messages (from context_bundle), tools (from filtered_tools), phase
- Replace the `model_router.call()` call with `controller.call()` for this purpose
- Existing telemetry (`record_model_call_start` / `record_model_call_end`) is still called — or moved inside controller and deduplicated

Allowed files: `agent.py` (wiring seam only), `runtime/llm_runtime_controller.py` (if minor interface changes needed)

Forbidden: `runtime/context_manager.py`, `runtime/skill_policy.py`, `tests/e2e/`, any paid LLM calls

Stop conditions:
- Wiring breaks existing `plan_diff_editor` path → revert
- Any of the 604 tests fail → investigate before proceeding
- Controller call changes output format observed by downstream code → design schema first

---

## 9. What Not to Do

| Shortcut | Why it's risky |
|---|---|
| Build prompt packs before wiring (S5-002 before S5-001) | Dead code — packs are never used if the controller isn't wired |
| Optimize context before measuring (S5-005/006 before S5-007) | You won't know if the change helped or hurt |
| Use Responses API or previous_response_id | Breaks backend-as-truth: provider controls context, not AutoWorkbench |
| Remove safety rules from system prompt to save tokens | Non-negotiable. Correctness must not drop. Use regression gate (S5-015) to enforce this |
| Route real cheap model before contract exists (S5-008 without schema) | Routing to a weaker model without schema validation → unpredictable output, hard to debug |
| Implement all 14 purposes in S5-001 | Too broad. Wire step_plan_normalizer first, verify, then expand |
| Skip FakeLLM suite and verify with paid E2E | Expensive, slow, and not repeatable in CI |
| Trust ModelCallTelemetry.skill_tokens without per-skill attribution | skill_tokens is a raw count, not skill names — you can't debug what you can't see |
| Implement page intelligence before fixture pages exist | Nothing to test against |
| Put stable prefix last in prompt (cache miss every call) | Provider caches prefix only. If instructions are after dynamic content, no cache hits |

---

## 10. Open Questions for User Approval

The following require a decision before implementation begins:

1. **Controller instantiation pattern for step_plan_normalizer**
   - Option A: Create `_plan_normalizer_controller` on `AgentLoop.__init__` (same as `_plan_diff_editor_controller`)
   - Option B: Use a single shared `_llm_purpose_controller` that accepts purpose at call time
   - **Recommendation:** Option B avoids controller proliferation (14 purposes → 14 controllers would be unmanageable)

2. **Skill content source**
   - Where do compact skill summaries live? Are they short strings in skill_policy.py? Separate files? Dynamically generated?
   - **Recommendation:** Store compact summaries as short string constants in `runtime/skill_summaries.py`, keyed by skill name. Full skills are loaded from existing skill files.

3. **Token reduction acceptance threshold for S5-013**
   - Is ≤110% of baseline acceptable (allow up to 10% increase from measurement variance)?
   - Or must Sprint 5 produce a measurable reduction (e.g., ≥10% fewer tokens)?
   - **Recommendation:** Define ≥10% reduction for targeted call types (step_plan_normalizer), ≤110% for full flow.

4. **plan_diff_editor is already wired — should S5-001 be considered done for that purpose?**
   - If yes, S5-001 scope = step_plan_normalizer only. plan_diff_editor is already a reference implementation.
   - **Recommendation:** Yes. S5-001 is step_plan_normalizer. plan_diff_editor is the reference pattern.

5. **Cached tokens field in telemetry**
   - OpenAI returns `usage.prompt_tokens_details.cached_tokens` only if prompt caching occurred.
   - Should S5-007 add this field as nullable (None if no cache hit)?
   - **Recommendation:** Yes, nullable. Log 0 if not present.

6. **Recovery context: last 1 failure or last N?**
   - `recovery_recent_evidence` in ContextManager currently picks last 4 messages matching failure markers.
   - Is this sufficient? Or should recovery see all retry attempts for the current step?
   - **Recommendation:** All retry attempts for the current failed step (bounded by step_id), not just last 4 messages.

7. **FakeLLM schema fidelity**
   - Should FakeLLM stubs return the exact same JSON schema that the real controller validates, or a simplified version?
   - **Recommendation:** Exact schema. If the fake output doesn't match the validator, the test is catching a real problem.

8. **Page Intelligence model**
   - Should the cheap model for page_intelligence_summarizer be a different endpoint (e.g., gpt-4o-mini vs gpt-4o for main), or the same model with a smaller context?
   - **Recommendation:** Same model (gpt-4o-mini) for MVP. Model routing contract (S5-008) can add differentiation later.
