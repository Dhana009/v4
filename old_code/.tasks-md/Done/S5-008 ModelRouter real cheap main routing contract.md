# S5-008 ModelRouter real cheap/main routing contract

Status: Done
Sprint: Sprint 5
Type: Story
Owner: Dhanunjaya
Closed: 2026-05-12
Priority: P1
Source docs: PRD v2.3 07_MULTI_MODEL_ORCHESTRATION.md, runtime/model_router.py

## Resolution

Extended `runtime/model_router.py`:
- Added `ModelResolution` dataclass exposing `requested`, `resolved_model`, `fallback_used`, `fallback_chain`.
- Added `resolve_model()` returning resolution metadata.
- Added `ModelRouter.resolve()`, `.resolve_model_name()`, `.resolve_for_purpose()`, `.last_resolution`.
- Added `strict=True` mode that fails closed for `cheap`/`debug` when not configured.
- Added `purpose_model_classes` map to resolve by purpose.
- Extended `[MODEL_ROUTER]` log line with `requested=`, `fallback_used=`, `chain=` fields for observability.

Existing behavior preserved:
- Default routing still resolves to `gpt-4o-mini` when nothing configured.
- Internal `main` / `cheap` / `debug` classes still resolve to configured providers with deterministic fallback chain.
- Explicit provider names (e.g. `gpt-4o-mini`) still pass through.
- Unknown class names still raise `ValueError` (fail closed).

## Tests

`tests/test_model_router.py` — 19 tests, all passing:
- `test_resolve_model_debug_falls_back_to_main_when_not_configured`
- `test_resolve_model_cheap_uses_explicit_configured_cheap_model`
- `test_resolve_model_strict_cheap_fails_when_unconfigured`
- `test_resolve_model_strict_debug_fails_when_unconfigured`
- `test_resolve_model_returns_resolution_metadata`
- `test_model_router_records_last_resolution`
- `test_model_router_resolve_for_purpose_uses_registered_class`
- `test_model_router_resolve_for_purpose_rejects_unknown_purpose`
- `test_model_router_strict_mode_fails_cheap_without_config`
- `test_model_router_call_logs_resolution_metadata`
- `test_model_router_call_resolves_cheap_to_configured_cheap_provider`
- plus 8 pre-existing tests still passing

Sprint 5 regression suite (`test_sprint5_llm_runtime_guardrails.py`, `test_tool_policy_contract.py`, `test_tool_schema_filter.py`, `test_llm_runtime_controller_contract.py`): 54 tests passing.

## Evidence

- `runtime/model_router.py` (extended)
- `tests/test_model_router.py` (11 new tests)
- No paid LLM, no live calls, no controller wiring change.

## Problem / Goal

**Problem:** model_router.py is currently a thin passthrough. It doesn't route purpose/model_class to different model endpoints. All calls use the same model regardless of purpose="cheap" or "main".

**Goal:** Turn model_router into a contract-tested router. Route purpose/model_class to configured model names (e.g., page_intelligence → "gpt-4o-mini", planning → "gpt-4o"). Test with fake provider without real API keys.

## Scope

- Extend ModelRouter to accept: purpose, model_class, purpose_registry
- Route model_class="cheap" → configured_cheap_model (e.g., "gpt-4o-mini")
- Route model_class="main" → configured_main_model (e.g., "gpt-4o")
- Fallback behavior if cheap model unavailable (explicit fallback chain)
- No production key/config changes
- Fake provider tests only

Out of scope:
- Actual cheap/nano model provider migration
- Production key management
- Live model calls

## Required unit tests

- `test_model_router_routing_logic.py`:
  - route(purpose="page_intelligence_summarizer", model_class="cheap") returns cheap model name
  - route(purpose="step_plan_normalizer", model_class="main") returns main model name
  - Fallback behavior is explicit
- `test_model_router_config.py`:
  - Router accepts and stores model_class config
  - Fallback chain is deterministic

## Required contract tests

- `test_model_router_contract.py`:
  - No fallback to expensive model for cheap purposes (fail-closed if no cheap model)
  - Main model routes correctly
  - Explicit fallback is logged

## Required integration tests

- `test_model_routing_with_fake_provider.py`:
  - Fake provider receives correct model name based on purpose
  - Call succeeds for cheap and main models
  - Telemetry includes model_class

## Fixture/page needs

None.

## Paid E2E requirement

None.

## Acceptance criteria

- [ ] ModelRouter extended with routing logic
- [ ] model_class="cheap" routes to configured cheap model
- [ ] model_class="main" routes to configured main model
- [ ] Fallback is explicit and logged
- [ ] No fallback to expensive model for cheap purposes
- [ ] Contract tests prove routing correctness
- [ ] No production keys or config changes
- [ ] Fake provider tests pass

## Evidence

Will include:
- Extended ModelRouter implementation
- Unit test output showing routing decisions
- Contract test output proving no fallback to expensive
- Integration test output with fake provider
- Telemetry sample showing model_class

## Verification commands/results

```bash
pytest tests/test_model_router_routing_logic.py -v
pytest tests/test_model_router_config.py -v
pytest tests/test_model_router_contract.py -v
pytest tests/test_model_routing_with_fake_provider.py -v

# Verify cheap model routing
grep -E "cheap.*model_name|main.*model_name" tests/test_model_router_routing_logic.py
```

## Risk

- **Low:** Fallback logic may be incomplete if models become unavailable
- **Low:** Config may need environment variables (deferred to production deployment)

## Mitigation

- Contract test explicit about fallback behavior
- Fallback chain is deterministic
- Config can be mocked in tests
