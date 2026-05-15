"""Unit tests for runtime.multi_agent_orchestrator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from runtime.multi_agent_orchestrator import (
    AgentInvocation,
    AgentRole,
    MultiAgentOrchestrator,
    build_agent_status_event,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_orchestrator(response: dict | None = None) -> MultiAgentOrchestrator:
    controller = AsyncMock()
    controller.call = AsyncMock(return_value=response or {"ok": True})
    return MultiAgentOrchestrator(controller)


# ---------------------------------------------------------------------------
# 1. role_for_purpose maps the 5 main purpose groups
# ---------------------------------------------------------------------------

def test_role_for_purpose_main_groups() -> None:
    orc = _make_orchestrator()
    assert orc.role_for_purpose("journey_planner") == AgentRole.MAIN_ORCHESTRATOR
    assert orc.role_for_purpose("page_intelligence") == AgentRole.PAGE_INTELLIGENCE
    assert orc.role_for_purpose("step_runner") == AgentRole.STEP_RUNNER
    assert orc.role_for_purpose("debug_agent") == AgentRole.DEBUG_AGENT
    assert orc.role_for_purpose("codegen_reviewer") == AgentRole.CODEGEN_REVIEWER


# ---------------------------------------------------------------------------
# 2. invoke() with a fake controller returns wrapped response
# ---------------------------------------------------------------------------

def test_invoke_returns_wrapped_response() -> None:
    orc = _make_orchestrator({"result": "done"})
    inv = AgentInvocation(
        role=AgentRole.STEP_RUNNER,
        purpose="step_runner",
        context={"step": 1},
    )
    result = asyncio.new_event_loop().run_until_complete(orc.invoke(inv))
    assert result["role"] == AgentRole.STEP_RUNNER.value
    assert result["purpose"] == "step_runner"
    assert result["response"] == {"result": "done"}


# ---------------------------------------------------------------------------
# 3. agent_invocation_id is unique + role-prefixed
# ---------------------------------------------------------------------------

def test_invocation_id_unique_and_role_prefixed() -> None:
    orc = _make_orchestrator()
    inv = AgentInvocation(
        role=AgentRole.DEBUG_AGENT,
        purpose="debug_agent",
        context={},
    )
    r1 = asyncio.new_event_loop().run_until_complete(orc.invoke(inv))
    r2 = asyncio.new_event_loop().run_until_complete(orc.invoke(inv))
    assert r1["agent_invocation_id"].startswith("debug_agent-")
    assert r2["agent_invocation_id"].startswith("debug_agent-")
    assert r1["agent_invocation_id"] != r2["agent_invocation_id"]


# ---------------------------------------------------------------------------
# 4. list_active_invocations() empty when none in flight
# ---------------------------------------------------------------------------

def test_list_active_invocations_empty_at_rest() -> None:
    orc = _make_orchestrator()
    assert orc.list_active_invocations() == []


# ---------------------------------------------------------------------------
# 5. build_agent_status_event returns correct shape
# ---------------------------------------------------------------------------

def test_build_agent_status_event_shape() -> None:
    invocation = {
        "agent_invocation_id": "step_runner-abc123",
        "role": "step_runner",
        "purpose": "step_runner",
        "parent_run_id": "run-1",
        "parent_step_id": "step-1",
    }
    event = build_agent_status_event(invocation, "completed")
    assert event["type"] == "agent_status"
    payload = event["payload"]
    assert payload["status"] == "completed"
    assert payload["agent_invocation_id"] == "step_runner-abc123"
    assert payload["role"] == "step_runner"
    assert payload["error"] is None


# ---------------------------------------------------------------------------
# 6. build_agent_status_event includes error when provided
# ---------------------------------------------------------------------------

def test_build_agent_status_event_with_error() -> None:
    invocation = {
        "agent_invocation_id": "debug_agent-xyz",
        "role": "debug_agent",
        "purpose": "debug_failure",
        "parent_run_id": None,
        "parent_step_id": None,
    }
    event = build_agent_status_event(invocation, "failed", error="timeout exceeded")
    assert event["payload"]["status"] == "failed"
    assert event["payload"]["error"] == "timeout exceeded"
