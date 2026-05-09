# S5-007 Token report attribution upgrade

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, AGENTS.md token baseline, runtime/telemetry.py, runtime/token_report.py

## Problem / Goal

**Problem:** Current token reports don't show exact prompt pack, skill names, skill levels, or context bucket breakdown. Can't verify token reduction vs baseline or attribute costs.

**Goal:** Upgrade token_report.py to show exact: prompt_pack_id, skill_names, skill_levels, model_class, context_bucket, tool_schema_cost, history_tokens, DOM_tokens. Enable token attribution and comparison.

## Evidence

Status: Done

Implemented:
- `runtime/telemetry.py`: Added 8 new optional fields to ModelCallTelemetry and record_model_call_start(): prompt_pack_id, prompt_pack_version, skills_loaded (list), skill_levels (list), model_class, context_bucket, cached_tokens, prefix_hash
- `runtime/telemetry.py`: _format_telemetry_line() emits new fields when set (None → omitted)
- `runtime/telemetry.py`: record_model_call_end() extracts cached_tokens from usage.prompt_tokens_details.cached_tokens (OpenAI style) when not already set
- `runtime/token_report.py`: build_token_report() aggregates prompt_pack_ids, model_classes, context_buckets, total_cached_tokens per report (empty-records path included)

Telemetry fields added:
- prompt_pack_id, prompt_pack_version, skills_loaded, skill_levels, model_class, context_bucket, cached_tokens, prefix_hash

Token report fields added:
- prompt_pack_ids, model_classes, context_buckets, total_cached_tokens

Tests added:
- test_telemetry_breakdown.py: 9 new tests covering field acceptance, defaults, line emission, cached_tokens extraction from usage, preloaded value protection, backward compat
- test_token_report.py: 10 new tests covering new report fields, aggregation, deduplication, backward compat, empty report

Commands run:
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q` → 46 passed
- `python -m pytest tests/ -q` → 647 passed

Changed files:
- runtime/telemetry.py
- runtime/token_report.py
- tests/test_telemetry_breakdown.py
- tests/test_token_report.py

Commit: feat: add sprint 5 fake llm and token attribution foundation

## Scope

- Extend telemetry.ModelCallTelemetry to include: prompt_pack_id, prompt_pack_version, skills_loaded (list), skill_levels (list), model_class, context_bucket, tool_schema_tokens, history_tokens, dom_tokens
- Upgrade token_report.py to breakdown by: purpose, model, prompt_pack_id, skill names, tool_schema, context bucket, DOM
- Generate per-flow token report (e.g., planning calls: 2 calls, 1200 tokens, [prompt_pack_id, skill_names])
- No behavior changes, only telemetry recording

Out of scope:
- Changing prompt packs or skill loading (S5-002/003)
- Changing context compaction logic (S5-005/006)
- Token budget enforcement (S5-015)

## Required unit tests

- `test_telemetry_extended_fields.py`:
  - ModelCallTelemetry includes all new fields
  - Skills_loaded is list of strings
  - Skill_levels is list of strings
  - model_class is "cheap" or "main"
  - Context_bucket is "planning" | "correction" | "recovery" | "other"
- `test_token_report_attribution.py`:
  - token_report.json includes breakdown by purpose
  - Each call record includes prompt_pack_id, skill_names, tool_schema_tokens
  - Summary table aggregates by purpose and prompt_pack_id

## Required contract tests

- `test_token_report_schema.py`:
  - token_report.json matches expected schema
  - All required fields present
  - Token sums add up correctly

## Required integration tests

- `test_planning_token_attribution.py`:
  - Planning call generates report with skill_names, tool_schema_tokens, prompt_pack_id
  - Report is parseable JSON
  - Token breakdown is accurate

## Fixture/page needs

None.

## Paid E2E requirement

None.

## Acceptance criteria

- [ ] Telemetry extended with prompt_pack_id, skills_loaded, skill_levels, model_class, context_bucket, token breakdown
- [ ] token_report.py generates detailed breakdown by purpose, model, prompt_pack_id, skill names
- [ ] Per-call tokens attributed to: prompt_pack, skill names (with levels), tool_schema, history, DOM
- [ ] Token report is valid JSON and parseable
- [ ] Comparison with baseline token report is possible (old vs new by purpose)
- [ ] All fields documented in schema

## Evidence

Will include:
- Extended ModelCallTelemetry implementation
- Upgraded token_report.py with attribution logic
- Unit test output showing extended fields
- Contract test output showing schema validity
- Sample token_report.json with full breakdown
- Comparison table: baseline vs S5-007 attribution

## Verification commands/results

```bash
pytest tests/test_telemetry_extended_fields.py -v
pytest tests/test_token_report_attribution.py -v
pytest tests/test_token_report_schema.py -v
pytest tests/test_planning_token_attribution.py -v

# Sample report generation
python -c "from runtime.token_report import TokenReport; r = TokenReport(...); print(json.dumps(r.to_dict(), indent=2))"
```

## Risk

- **Low:** Additional telemetry fields may increase log overhead slightly
- **Low:** Schema changes to telemetry may break existing log parsing tools (version bump needed)

## Mitigation

- Telemetry fields are additive (no breaking changes)
- Schema versioning in telemetry.py
- Token_report.py version field for future evolution
