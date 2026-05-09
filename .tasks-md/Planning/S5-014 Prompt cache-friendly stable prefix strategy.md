# S5-014 Prompt/cache-friendly stable prefix strategy

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 02_LLM_RUNTIME.md, prompt-caching best practices

## Problem / Goal

**Problem:** Prompt packs (S5-002) have static prefix + dynamic suffix. If prefix ordering/content is stable, provider prompt cache can reuse it across calls.

**Goal:** Structure prompt packs so stable prefix is deterministic and cacheable. Generate prefix hash for telemetry. Enable provider-level caching (if provider supports it).

## Scope

- Extend prompt_pack_builder.py to separate: stable_prefix, dynamic_suffix
- Stable prefix includes: core safety rules, phase instructions, recovery scope (if applicable)
- Dynamic suffix includes: active plan/correction text, context data
- Generate prefix_hash: content-hash of stable prefix
- Telemetry includes: prompt_pack_id, prefix_hash
- Document stable prefix structure per purpose

Out of scope:
- Relying on provider cache for runtime truth (cache is performance optimization only)
- Changing safety rules
- Changing output schema

## Required unit tests

- `test_prompt_pack_stable_prefix.py`:
  - Stable prefix is deterministic (same content → same hash)
  - Dynamic suffix is separated
  - Prefix doesn't include variable data (plan, correction, context)
- `test_prefix_hash_determinism.py`:
  - Same purpose/version → same prefix_hash
  - Hash doesn't change across calls

## Required contract tests

- `test_stable_prefix_structure.py`:
  - Stable prefix includes all critical safety rules
  - Dynamic suffix is pure context/plan/correction
  - No mixing of stable/dynamic content

## Required integration tests

- `test_planning_call_prefix_hash.py`:
  - Planning call generates correct prefix_hash
  - Telemetry includes prefix_hash
  - Hash is deterministic

## Fixture/page needs

None.

## Paid E2E requirement

None.

## Acceptance criteria

- [ ] Stable prefix is separated from dynamic suffix in prompt packs
- [ ] Stable prefix is deterministic and hashable
- [ ] prefix_hash included in telemetry
- [ ] prefix_hash is same across identical calls to same purpose
- [ ] Dynamic suffix contains plan/correction/context only
- [ ] Documentation explains stable prefix structure per purpose
- [ ] No behavior change; purely structural

## Evidence

Will include:
- Updated prompt_pack_builder.py with prefix/suffix separation
- Unit test output showing hash determinism
- Telemetry sample showing prefix_hash
- Documentation of stable prefix per purpose
- Hash consistency report

## Verification commands/results

```bash
pytest tests/test_prompt_pack_stable_prefix.py -v
pytest tests/test_prefix_hash_determinism.py -v
pytest tests/test_stable_prefix_structure.py -v
pytest tests/test_planning_call_prefix_hash.py -v

# Verify hash determinism
python -c "
from runtime.prompt_pack_builder import build_step_plan_normalizer_pack
pack1 = build_step_plan_normalizer_pack()
pack2 = build_step_plan_normalizer_pack()
print(f'Hash 1: {pack1[\"prefix_hash\"]}')
print(f'Hash 2: {pack2[\"prefix_hash\"]}')
print(f'Match: {pack1[\"prefix_hash\"] == pack2[\"prefix_hash\"]}')"
```

## Risk

- **Low:** Provider cache behavior varies (acceptable, optimization is best-effort)
- **Low:** Prefix structure may need future adjustments (hash versioning handles that)

## Mitigation

- Hash versioning: include prompt_pack_version in hash
- Documentation is explicit about cache optimization only
- Cache is transparent (no behavior change)
