# S6-0107 Controller Call-Site Inventory

**Sprint:** Sprint 6  
**Cluster:** 1  
**Story:** S6-0107  
**Date:** 2026-05-12  
**Status:** Complete  

---

## Summary

All production LLM call sites classified. Controller ownership verified for purpose-dispatched paths.
Direct provider wrapper files (`llm.py`, `llm/client.py`, `a.py`) are legacy/dead-code, not hooked into
the purpose dispatch system.

---

## Call-Site Classification

| File | Call site | Classification | Notes |
|---|---|---|---|
| `agent.py:160` | `LLMRuntimeController(purpose_registry=PURPOSE_REGISTRY, ...)` | **controller-owned** | Primary instantiation with full registry |
| `agent.py:168` | `self._plan_diff_editor_controller = self._llm_runtime_controller` | **controller-owned** | Alias for plan_diff_editor — same controller |
| `agent.py:3849` | `controller = getattr(self, "_llm_runtime_controller", None)` | **controller-owned** | Lookup of controller for call dispatch |
| `agent.py:3896` | `controller = getattr(self, "_llm_runtime_controller", None)` | **controller-owned** | Lookup of controller for call dispatch |
| `agent.py:3990` | `isinstance(controller, LLMRuntimeController)` | **controller-owned** | Type guard before dispatch |
| `runtime/model_router.py:247` | `await request.client.chat.completions.create(**payload)` | **controller-owned** | Inside the router called BY the controller; not an independent bypass |
| `runtime/llm_runtime_controller.py:1062` | `chat.completions.create` (referenced in error message only) | **controller-owned** | Error-path only, not a direct call |
| `llm/client.py:26` | `await self.client.chat.completions.create(...)` | **legacy wrapper** | Direct AsyncOpenAI; no purpose awareness; pending migration |
| `llm.py:26` | `await self.client.chat.completions.create(...)` | **dead code / legacy** | Root-level duplicate of `llm/client.py`; not used in production path |
| `a.py:12` | `client.chat.completions.create(...)` | **dead code / scratch** | Scratch file; no import from production code |
| `tests/fake_llm_factory.py:10` | `await client.chat.completions.create(...)` | **test harness only** | Used in tests to simulate real LLM responses; not a production bypass |
| `tests/e2e/harness.py:1149` | `openai_key = ...` (env var read only) | **test E2E setup** | E2E harness only; reads API key but does not call LLM directly |

---

## Direct Provider Files — Legacy/Pending Migration

### `llm/client.py` (LLMClient)

- **Status:** Legacy direct wrapper
- **Used by:** `agent.py` imports `LLMClient` at line 19 and instantiates at line 149 (`self.llm = LLMClient()`)
- **Problem:** `LLMClient` wraps AsyncOpenAI directly; it has no purpose awareness, no ALLOWED_PURPOSES check, no registry lookup
- **Risk:** `agent.py` may be calling `self.llm` for some LLM calls outside the controller
- **Action needed:** Cluster 2 migration — identify all `self.llm.call(...)` uses in agent.py; migrate to controller
- **Guard test:** `tests/test_llm_controller_callsite_guard.py::test_llm_client_has_no_purpose_awareness` — verifies no purpose_registry on LLMClient

### `llm.py` (root-level)

- **Status:** Dead code duplicate
- **Used by:** Nothing in production imports from `llm.py` directly (it's shadowed by `llm/` package)
- **Action needed:** Cluster 2 cleanup — can be removed
- **Guard test:** Not testable (dead code); documented here

### `a.py`

- **Status:** Scratch file
- **Used by:** Nothing
- **Action needed:** Remove in cleanup pass
- **Guard test:** Not applicable (dead code)

---

## agent.py LLM Call Analysis

`agent.py` has two LLM client references:
1. `self.llm = LLMClient()` — legacy direct wrapper (line 149)
2. `self._llm_runtime_controller = LLMRuntimeController(...)` — controller (line 160)

**Risk:** Any `self.llm.call(...)` usage in agent.py bypasses the controller and the purpose registry.

**Cluster 2 action required:** Search `agent.py` for all `self.llm` call sites and determine which need migration to `self._llm_runtime_controller.call(purpose=...)`.

---

## model_router.py

- **Status:** Controller-owned path
- `runtime/model_router.py` is called by `LLMRuntimeController._call_model()` when `client` is None
- This is the intended path: controller → model_router → provider
- No direct provider bypass — model_router requires a request object from the controller

---

## Guard Tests Added

File: `tests/test_llm_controller_callsite_guard.py`

| Test | Guards |
|---|---|
| `test_controller_has_purpose_registry` | LLMRuntimeController has PURPOSE_REGISTRY |
| `test_controller_purpose_registry_has_all_14` | Registry has all 14 purposes |
| `test_controller_raises_for_unknown_purpose` | Unknown purpose raises ValueError |
| `test_controller_raises_for_empty_purpose` | Empty purpose raises ValueError |
| `test_allowed_purposes_matches_policy_registry` | ALLOWED_PURPOSES and POLICY_REGISTRY do not drift |
| `test_llm_py_is_not_a_purpose` | llm.py not an LLM purpose |
| `test_a_py_is_not_a_purpose` | a.py not an LLM purpose |
| `test_llm_client_is_not_a_purpose` | llm/client.py not an LLM purpose |
| `test_llm_py_does_not_use_controller` | llm/client.py doesn't import LLMRuntimeController |
| `test_llm_client_has_no_purpose_awareness` | LLMClient has no purpose_registry |
| `test_purpose_registry_rejects_unknown` | PURPOSE_REGISTRY fail-closed |
| `test_purpose_registry_rejects_none` | PURPOSE_REGISTRY fail-closed for None |
| `test_policy_registry_rejects_unknown` | POLICY_REGISTRY fail-closed |
| `test_policy_registry_rejects_none` | POLICY_REGISTRY fail-closed for None |
| `test_model_router_not_imported_by_llm_py` | model_router not in legacy wrapper |
| `test_model_router_is_imported_by_controller` | model_router IS in controller |
| `test_agent_imports_llm_runtime_controller` | agent.py imports LLMRuntimeController |
| `test_agent_instantiates_controller` | agent.py instantiates LLMRuntimeController |

All 18 guard tests pass.

---

## Open Migration Work (Not Cluster 1 Scope)

| Call site | Migration story | Priority |
|---|---|---|
| `agent.py self.llm.call(...)` uses | Cluster 2 S6-0201+ | High |
| `llm.py` removal | Cluster 2 cleanup | Low |
| `a.py` removal | Cluster 2 cleanup | Low |
| `llm/client.py` direct wrapper → purpose-aware client | Cluster 2 S6-0201+ | High |

---

## Validation Evidence

```bash
python -m pytest tests/test_llm_controller_callsite_guard.py -q
# 18 passed
```
