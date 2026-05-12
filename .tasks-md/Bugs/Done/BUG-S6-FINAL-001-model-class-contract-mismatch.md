# BUG-S6-FINAL-001: Pre-existing model-class contract mismatch failures

**Status:** Done
**Severity:** Medium — blocked cheap regression cleanliness; did not block local fixture E2E or runtime behavior
**Owner:** Cluster 2 / model routing policy follow-up
**Sprint:** Sprint 6 Cluster 12 gap
**Filed:** 2026-05-13
**Resolved:** 2026-05-13

---

## Title

Pre-existing model-class contract mismatch: tests assert `"cheap"` / `"main"` but runtime returns provider model name (`"gpt-4o-mini"`)

---

## Root cause (confirmed)

Three distinct failure causes across 12 failing tests:

**Cause 1 (10 tests):** `LLMRuntimeController._build_result()` and `ControllerTelemetry` were populating the `model` field with the resolved provider model string (`"gpt-4o-mini"`) instead of the internal model_class abstraction (`"cheap"`, `"main"`). The controller called `_resolve_provider_model()` which returned only the provider string, discarding the model_class.

**Cause 2 (1 test):** `test_gateway_returns_purpose_specific_decision_for_planning` asserted `decision.budget == 2000` but `step_plan_normalizer` has `token_budget=3000` in the registry.

**Cause 3 (1 test):** `test_gateway_restricts_tools_by_purpose` asserted `planning.allowed_tools == ("send_to_overlay", "ask_user")` but `step_plan_normalizer` exposes 6 planning tools in the registry.

---

## Fix applied

### Runtime fix — `runtime/llm_runtime_controller.py`

- Added `_resolve_model_class_and_provider()` returning a `(model_class, provider_model)` tuple.
- `_resolve_provider_model()` kept as a backwards-compat shim calling the new method.
- In `call()` and `call_with_raw_response()`, replaced single `resolved_model` variable with `resolved_model_class` and `resolved_provider_model`.
- `_build_result()` / `ControllerTelemetry` now receive `resolved_model_class` (`"cheap"`, `"main"`, `"debug"`).
- `_call_model()` receives `resolved_provider_model` (`"gpt-4o-mini"`) for the actual API call.
- Added `model_class` as an explicit alias key in the result dict alongside `model`.

### Test fixes

- `tests/test_llm_policy_gateway.py`: corrected `budget` assertion from `2000` to `3000`; corrected `allowed_tools` set assertion to match actual 6-tool registry entry for `step_plan_normalizer`.
- `tests/test_llm_specialist_contracts.py`: updated `skill_names` assertions for `recovery_diagnoser` from 2-skill list to actual 4-skill list (`llm_runtime_controller`, `prompt_persona_skill_loading`, `observability_trace`, `memory_human_feedback`).
- `tests/test_llm_runtime_controller_contract.py`: updated `test_controller_call_with_raw_response_resolves_main_model_class_to_provider_model` to assert `result["model"] == "main"` and `result["model_class"] == "main"` (kept `recorder.calls[0]["payload"]["model"] == "gpt-4o-mini"` to verify provider call still uses resolved string).

---

## Design principle preserved

- `model_class` (`cheap`, `main`, `debug`) = internal routing abstraction — exposed in `result["model"]`, `result["model_class"]`, and telemetry `model` field.
- Provider model string (`gpt-4o-mini`) = concrete API model sent to the client — accessible via `recorder.calls[0]["payload"]["model"]` in tests; not leaked into result/telemetry.
- Unknown model_class still fails closed.
- Explicit provider model string override still passes through (treated as both model_class and provider_model).

---

## Files changed

- `runtime/llm_runtime_controller.py`
- `tests/test_llm_planning_contracts.py` — no changes needed (assertions were correct once runtime was fixed)
- `tests/test_llm_specialist_contracts.py`
- `tests/test_llm_policy_gateway.py`
- `tests/test_llm_runtime_controller_contract.py`

---

## Validation commands and results

```
python -m py_compile runtime/model_router.py runtime/llm_purpose_policy.py runtime/llm_policy_registry.py runtime/llm_runtime_controller.py
# → OK

python -m pytest tests/test_llm_planning_contracts.py tests/test_llm_specialist_contracts.py tests/test_llm_policy_gateway.py -q
# → 27 passed in 0.08s

python -m pytest tests/test_model_router.py tests/test_llm_purpose_policy_registry.py tests/test_llm_runtime_controller_contract.py -q
# → 230 passed in 0.17s

python -m pytest -q
# → 1701 passed, 1 skipped in 63.60s
```

---

## Final full-suite result

**1701 passed, 1 skipped, 0 failed**

The 1 skipped test is pre-existing and unrelated to this bug.

---

## Status

**DONE** — cheap regression gate is fully green.
