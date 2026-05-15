"""
S6-0107: Controller call-site inventory and migration guard — guard tests.

Goal: Prevent known direct-provider call sites from bypassing the controller.
Source rule: Runtime Policy Spec — every LLM call must go through LLMRuntimeController.

Known call-site classification:
  controller-owned:   agent.py (uses LLMRuntimeController), runtime/model_router.py (inside controller path)
  legacy/dead-code:   llm.py (direct AsyncOpenAI wrapper), a.py (scratch file), llm/client.py (direct wrapper)
  pending-migration:  agent.py LLMClient usage (wraps controller but is a direct client layer)

Guard tests:
- LLMRuntimeController is the only path for purpose-dispatched calls (architecture seam)
- llm.py / llm/client.py / a.py do NOT appear on ALLOWED_PURPOSES list
- Direct call sites (llm.py etc.) are classified as legacy/pending migration
- PurposeRegistry cannot be bypassed via direct OpenAI calls in test harness
"""
from __future__ import annotations

import importlib
import inspect

import pytest

from runtime.llm_runtime_controller import (
    ALLOWED_PURPOSES,
    LLMRuntimeController,
    PURPOSE_REGISTRY,
)
from runtime.llm_policy_registry import POLICY_REGISTRY


# ---------------------------------------------------------------------------
# 1. LLMRuntimeController is the declared registry-backed controller
# ---------------------------------------------------------------------------

def test_controller_has_purpose_registry():
    """LLMRuntimeController must have a PURPOSE_REGISTRY class attribute."""
    assert hasattr(LLMRuntimeController, "PURPOSE_REGISTRY")
    registry = LLMRuntimeController.PURPOSE_REGISTRY
    assert registry is not None


def test_controller_purpose_registry_has_all_14():
    # Updated to 17: added journey_classifier, failure_classifier, agent_fallback
    # per feat(runtime/agent): close LLM Runtime Controller bypass + route classifiers.
    registry = LLMRuntimeController.PURPOSE_REGISTRY
    purposes = set(registry.list_purposes())
    assert len(purposes) == 17


def test_controller_raises_for_unknown_purpose():
    """LLMRuntimeController._resolve_policy raises ValueError for unknown purpose."""
    from unittest.mock import MagicMock
    controller = LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=MagicMock(),
    )
    with pytest.raises(ValueError, match="Unknown LLM purpose"):
        controller._resolve_policy("totally_unknown_purpose_xyz")


def test_controller_raises_for_empty_purpose():
    from unittest.mock import MagicMock
    controller = LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=MagicMock(),
    )
    with pytest.raises(ValueError, match="Unknown LLM purpose"):
        controller._resolve_policy("")


# ---------------------------------------------------------------------------
# 2. Verify ALLOWED_PURPOSES matches POLICY_REGISTRY (no drift)
# ---------------------------------------------------------------------------

def test_allowed_purposes_matches_policy_registry():
    """ALLOWED_PURPOSES in llm_runtime_controller must match POLICY_REGISTRY."""
    allowed = set(ALLOWED_PURPOSES)
    registered = set(POLICY_REGISTRY.list_purposes())
    assert allowed == registered, (
        f"Drift detected!\n"
        f"  In ALLOWED_PURPOSES but not registry: {allowed - registered}\n"
        f"  In registry but not ALLOWED_PURPOSES: {registered - allowed}"
    )


# ---------------------------------------------------------------------------
# 3. Direct OpenAI call sites are classified (not on ALLOWED_PURPOSES)
# ---------------------------------------------------------------------------

def test_llm_py_is_not_a_purpose():
    """llm.py is a direct provider wrapper; it is NOT an LLM purpose."""
    assert "llm" not in ALLOWED_PURPOSES
    assert "LLMClient" not in ALLOWED_PURPOSES


def test_a_py_is_not_a_purpose():
    """a.py is a scratch file; it is NOT an LLM purpose."""
    assert "a" not in ALLOWED_PURPOSES


def test_llm_client_is_not_a_purpose():
    """llm/client.py is a direct provider wrapper; NOT an LLM purpose."""
    assert "client" not in ALLOWED_PURPOSES
    assert "llm_client" not in ALLOWED_PURPOSES


# ---------------------------------------------------------------------------
# 4. llm.py / llm/client.py are legacy thin wrappers (not purpose-dispatched)
# ---------------------------------------------------------------------------

def test_llm_py_does_not_use_controller():
    """llm.py must not import LLMRuntimeController (it's a legacy wrapper)."""
    llm_mod = importlib.import_module("llm.client")
    src = inspect.getsource(llm_mod)
    assert "LLMRuntimeController" not in src, (
        "llm/client.py must not use LLMRuntimeController — it is a legacy direct-client wrapper"
    )


def test_llm_client_has_no_purpose_awareness():
    """llm/client.py LLMClient must not dispatch by purpose (it's a raw wrapper)."""
    from llm.client import LLMClient
    # LLMClient should not have ALLOWED_PURPOSES or purpose_registry attributes
    assert not hasattr(LLMClient, "ALLOWED_PURPOSES")
    assert not hasattr(LLMClient, "purpose_registry")
    assert not hasattr(LLMClient, "PURPOSE_REGISTRY")


# ---------------------------------------------------------------------------
# 5. PurposeRegistry guard: unknown purposes rejected at registry level
# ---------------------------------------------------------------------------

def test_purpose_registry_rejects_unknown():
    with pytest.raises((ValueError, KeyError)):
        PURPOSE_REGISTRY.get_purpose_policy("not_a_real_purpose")


def test_purpose_registry_rejects_none():
    with pytest.raises((ValueError, KeyError, TypeError)):
        PURPOSE_REGISTRY.get_purpose_policy(None)  # type: ignore[arg-type]


def test_policy_registry_rejects_unknown():
    with pytest.raises((ValueError, KeyError)):
        POLICY_REGISTRY.get("not_a_real_purpose")


def test_policy_registry_rejects_none():
    with pytest.raises((ValueError, KeyError, TypeError)):
        POLICY_REGISTRY.get(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 6. model_router.py is inside the controller path (not an independent bypass)
# ---------------------------------------------------------------------------

def test_model_router_not_imported_by_llm_py():
    """llm/client.py must not use model_router (direct provider path only)."""
    llm_mod = importlib.import_module("llm.client")
    src = inspect.getsource(llm_mod)
    assert "model_router" not in src


def test_model_router_is_imported_by_controller():
    """LLMRuntimeController imports model_router — it is the correct path."""
    controller_mod = importlib.import_module("runtime.llm_runtime_controller")
    src = inspect.getsource(controller_mod)
    assert "model_router" in src


# ---------------------------------------------------------------------------
# 7. Agent.py uses LLMRuntimeController (seam guard)
# ---------------------------------------------------------------------------

def test_agent_imports_llm_runtime_controller():
    """agent.py must import LLMRuntimeController."""
    import agent as agent_mod
    src = inspect.getsource(agent_mod)
    assert "LLMRuntimeController" in src, (
        "agent.py must import and use LLMRuntimeController"
    )


def test_agent_instantiates_controller():
    """agent.py must instantiate LLMRuntimeController with purpose_registry."""
    import agent as agent_mod
    src = inspect.getsource(agent_mod)
    assert "LLMRuntimeController(" in src, (
        "agent.py must instantiate LLMRuntimeController"
    )
