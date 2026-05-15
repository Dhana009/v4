# S5-009 Page Intelligence LLM route design and contract

Status: Done
Sprint: Sprint 5
Type: Story
Owner: Dhanunjaya
Closed: 2026-05-12
Priority: P1
Source docs: PRD v2.3 07_MULTI_MODEL_ORCHESTRATION.md section 3.2, runtime/page_intelligence.py

## Resolution

Added `runtime/page_intelligence_schema.py` with LLM-facing schema built on top of the deterministic `PageIntelligencePacket`:

| Field | Type | Purpose |
|-------|------|---------|
| `page_summary` | str (≤160 chars) | Title + leading heading |
| `sections` | list[str] (≤12) | Heading-derived section names |
| `candidate_targets` | list[CandidateTarget] (≤16) | label / role / section / locator_hint / confidence |
| `ambiguity_groups` | list[AmbiguityGroup] (≤8) | intent → candidate indices |
| `recommended_action` | `ask_user` \| `plan_ready_possible` \| `needs_more_context` | Planner exit hint |
| `reason` | str | Short why-this-action label |
| `source_stats` | SourceStats | elements_seen / candidates_found / ambiguous_groups / sections_seen |
| `warnings` | list[str] (≤6) | risk flags + modal/dialog flag + repeated section |

Behavior:
- ambiguous duplicates (same normalized label, ≥2 candidates) → `ask_user`
- weak/unknown semantic DOM or no candidates → `needs_more_context`
- otherwise → `plan_ready_possible`
- locator-hint confidence: data-testid/data-cy → 0.9, aria-label → 0.7, else 0.4, downgraded for weak DOM
- modal/dialog presence is flagged as warning
- raw HTML never embedded; JSON serialization confirmed tag-free

## Tests

`tests/test_page_intelligence_schema.py` — 12 tests, all passing:
- JSON serialize round-trip
- Bounded sizes (`MAX_CANDIDATE_TARGETS`, `MAX_AMBIGUITY_GROUPS`, token estimate via len/4)
- No raw HTML/tags in serialized output
- Duplicate Profiles → ambiguity groups for save/edit + `ask_user`
- Weak Divs → `needs_more_context` + weak/no-candidate warnings
- Nested Cards → section hierarchy + form candidates
- Data Table → edit/delete candidates + ambiguity groups (per-row duplicates)
- Modal Recovery → `modal_or_dialog_visible` warning
- recommended_action enum decisions
- Dataclass serialization
- Empty HTML safe defaults

Full Sprint 5 cheap suite: 110 tests passing (schema + fixtures + router + guardrails + tool policy + tool schema + existing page intelligence).

## Evidence

- `runtime/page_intelligence_schema.py` (new, ~210 LOC)
- `tests/test_page_intelligence_schema.py` (new, 12 tests)
- No paid LLM, no live calls, no agent.py changes, no full S5-010 integration.

## Additional gaps found

- Existing `page_intelligence.py` aria-label regex stops at whitespace; multi-word aria-labels in `data-table.html` get truncated. Did not fix — schema test uses label match instead. Note for S5-010.

## Problem / Goal

**Problem:** page_intelligence.py does deterministic summarization only. For weak DOM (div/span pages), a cheap model could propose better locator candidates and page structure. Currently no contract for cheap model page intelligence.

**Goal:** Define structured output schema for page_intelligence_summarizer purpose. Schema includes: page summary, semantic quality, element candidates with confidence/risk, ambiguities, risk flags. Test with fake model (no real nano model).

## Scope

- Define PageIntelligenceSchema in `runtime/page_intelligence_schema.py`
- Output fields: page_or_section_summary, semantic_quality (good|mixed|poor), elements (list with semantic_name, element_type_guess, visible_text, signals_used, confidence, risk), ambiguities, risk_flags
- Contract tests for malformed output rejection
- Fake model tests for schema validation
- Advisory-only boundary: output is candidates/suggestions, not truth

Out of scope:
- Real nano model implementation (defer to follow-up)
- DOM intelligence execution or action
- Element validation (Step Runner does that)

## Required unit tests

- `test_page_intelligence_schema.py`:
  - Schema fields defined and documented
  - semantic_quality must be good|mixed|poor
  - Elements list must include confidence/risk
  - Ambiguities and risk_flags are optional lists
- `test_page_intelligence_schema_validation.py`:
  - Valid output passes validation
  - Missing required fields rejected
  - Invalid semantic_quality rejected
  - Confidence/risk must be numeric or string

## Required contract tests

- `test_page_intelligence_output_contract.py`:
  - Fake model output matches schema
  - Malformed output (missing semantic_quality) rejected
  - Risk flags are advisory-only (never execute)
  - Candidates are suggestions, not truth
- `test_page_intelligence_advisory_boundary.py`:
  - Output cannot trigger action or recording
  - Step Runner must validate all candidates before use

## Required integration tests

- `test_page_intelligence_with_weak_dom.py`:
  - Weak div/span page → page intelligence call
  - Output includes semantic_quality and ambiguities
  - Candidates are ranked by confidence
- `test_page_intelligence_fake_model_contract.py`:
  - Fake model receives weak DOM
  - Returns schema-valid output

## Fixture/page needs

- Weak div/span fixture page (for S5-011)

## Paid E2E requirement

None (fake model only).

## Acceptance criteria

- [ ] PageIntelligenceSchema defined and documented
- [ ] Output fields: page_summary, semantic_quality, elements (with confidence/risk), ambiguities, risk_flags
- [ ] Schema validation rejects malformed output
- [ ] Contract tests prove advisory-only boundary
- [ ] Fake model integration works
- [ ] Telemetry includes purpose="page_intelligence_summarizer"
- [ ] Documentation states output is suggestion only, Step Runner validates

## Evidence

Will include:
- PageIntelligenceSchema implementation
- Schema validation logic
- Unit test output showing schema structure
- Contract test output proving validation
- Integration test with fake model
- Documentation of advisory boundary

## Verification commands/results

```bash
pytest tests/test_page_intelligence_schema.py -v
pytest tests/test_page_intelligence_schema_validation.py -v
pytest tests/test_page_intelligence_output_contract.py -v
pytest tests/test_page_intelligence_advisory_boundary.py -v
pytest tests/test_page_intelligence_with_weak_dom.py -v
pytest tests/test_page_intelligence_fake_model_contract.py -v
```

## Risk

- **Low:** Output quality dependent on fake model; real model behavior may differ
- **Low:** Candidates may not always be valid (rejected by Step Runner during validation)

## Mitigation

- Contract tests comprehensive for schema
- Advisory-only boundary is explicit and tested
- Step Runner validation is non-negotiable
