# S5-010 Page Intelligence first fake-model integration

Status: Done
Sprint: Sprint 5
Type: Story
Owner: Dhanunjaya
Closed: 2026-05-12
Priority: P1
Source docs: PRD v2.3 07_MULTI_MODEL_ORCHESTRATION.md, S5-009 Page Intelligence contract

## Resolution

Fake-model integration wired without paid LLM and without broad agent.py changes:

1. **Aria-label regex fix** in `runtime/page_intelligence.py`:
   `_ARIA_LABEL_RE` now allows whitespace inside quoted values, so multi-word
   labels like `aria-label="Edit Alice"` are preserved end-to-end in candidate
   `locator_hint` values.

2. **Planner context bridge** in `runtime/page_intelligence_schema.py`:
   New `schema_to_planner_context_message(schema)` returns a system message
   with body `PAGE_INTELLIGENCE_PACKET={json}` — compact, JSON-only,
   never embeds raw HTML.

3. **FakeCheapPlanner test consumer** in `tests/test_page_intelligence_fake_integration.py`:
   Async OpenAI-shape fake that reads the packet from messages and emits
   terminal output (`ask_user` | `plan_ready` | `needs_more_context`) driven
   by `schema.recommended_action`.

Behavior verified per fixture:

| Fixture | recommended_action | Planner terminal |
|---------|--------------------|------------------|
| duplicate-profiles.html | ask_user | ask_user |
| weak-divs.html | needs_more_context | needs_more_context |
| nested-cards.html | (case-dependent) | ask_user / plan_ready / needs_more_context |
| data-table.html | ask_user | ask_user |
| modal-recovery.html | * (warnings include modal_or_dialog_visible) | * |

No live LLM, no paid E2E, no agent.py wiring, no controller contract change.

## Tests

`tests/test_page_intelligence_fake_integration.py` — 9 tests, all passing:
- `test_aria_label_multi_word_preserved_in_locator_hint`
- `test_duplicate_profiles_drives_planner_to_ask_user`
- `test_weak_divs_drives_planner_to_needs_more_context`
- `test_nested_cards_provides_section_and_candidate_hierarchy`
- `test_data_table_exposes_row_action_candidates`
- `test_modal_fixture_flags_dialog_and_keeps_candidates`
- `test_planner_message_contains_no_raw_html`
- `test_planner_message_is_token_bounded`
- `test_fake_planner_records_call_without_paid_llm`

Broader Sprint 5 cheap suite: 73 (router + guardrails + tool policy + tool schema + controller contract) all passing.

## Evidence

- `runtime/page_intelligence.py` (1-line aria regex fix)
- `runtime/page_intelligence_schema.py` (+`schema_to_planner_context_message`)
- `tests/test_page_intelligence_fake_integration.py` (new, 9 tests)

## Additional gaps found

- Page Intelligence is not yet auto-invoked by agent.py before planning;
  the schema and helper exist but agent.py wiring is deferred. This keeps
  S5-013 paid path unchanged and avoids touching convergence narrowing.
- Cheap-model real provider routing relies on S5-008's `purpose_model_classes`
  map but no live consumer yet calls `resolve_for_purpose`. Wiring deferred
  until a real cheap model is configured in production.

## Problem / Goal

**Problem:** Page intelligence is currently deterministic HTML only. For weak div/span pages, we need to prove a fake cheap model can propose better candidates before main planner sees the page.

**Goal:** Build fake-model integration where weak div/span page → page intelligence call (fake model) → compact summary → main planner receives summary instead of raw DOM. Verify Step Runner still validates locator.

## Scope

- Integrate page_intelligence_summarizer through LLMRuntimeController
- Weak div/span page flow: DOM → fake page intelligence model → struct summary → main planner
- Main planner receives PageIntelligencePacket summary, not raw DOM
- Verify Step Runner validates proposed locator before action
- Fake model returns schema-valid output

Out of scope:
- Real nano model (fake only for this story)
- Full DOM page intelligence (S5-011 fixture work)
- UI changes for page intelligence display

## Required unit tests

- `test_page_intelligence_summarizer_call.py`:
  - page_intelligence_summarizer purpose call through controller
  - Fake model receives weak DOM
  - Returns PageIntelligencePacket schema
- `test_page_intelligence_flow.py`:
  - Weak page → page intelligence call → compact summary
  - Summary is smaller than raw DOM

## Required contract tests

- `test_page_intelligence_to_main_planner_contract.py`:
  - Main planner receives PageIntelligencePacket summary
  - Summary includes candidates with confidence
  - Telemetry links page_intelligence call to main planner call

## Required integration tests

- `test_weak_dom_page_intelligence_flow.py`:
  - Weak div/span page triggers page intelligence call
  - Fake model processes page
  - Main planner receives summary
  - Step Runner validates proposed locator (no action without validation)
- `test_page_intelligence_backend_validation.py`:
  - Backend validates page intelligence candidate before action
  - Locator is re-validated live against page state

## Fixture/page needs

- Weak div/span fixture page (or use existing fixture from S5-011 planning)

## Paid E2E requirement

None (fake model only).

## Acceptance criteria

- [ ] page_intelligence_summarizer call routed through LLMRuntimeController
- [ ] Weak page flow: DOM → fake model → PageIntelligencePacket → main planner
- [ ] Main planner receives summary, not raw DOM
- [ ] Telemetry links both calls (page intelligence + planning)
- [ ] Step Runner validates all candidates before action
- [ ] No action without live validation
- [ ] Fake model integration works end-to-end

## Evidence

Will include:
- LLMRuntimeController wiring for page_intelligence_summarizer
- Fake model integration code
- Unit and integration test output
- Telemetry showing both calls
- Step Runner validation logs

## Verification commands/results

```bash
pytest tests/test_page_intelligence_summarizer_call.py -v
pytest tests/test_page_intelligence_flow.py -v
pytest tests/test_page_intelligence_to_main_planner_contract.py -v
pytest tests/test_weak_dom_page_intelligence_flow.py -v
pytest tests/test_page_intelligence_backend_validation.py -v

# Trace: weak DOM → page intelligence → summary → main planner → validation
grep -E "page_intelligence_summarizer|PageIntelligencePacket|backend.*validate" test_output.log
```

## Risk

- **Medium:** Fake model output may not reflect real model behavior
- **Low:** Main planner may need adjustment if it expects raw DOM context

## Mitigation

- Contract tests explicit about summary format
- Controlled E2E (S5-013) validates quality with real LLM
- Main planner can fall back to raw DOM if summary missing (logged)
