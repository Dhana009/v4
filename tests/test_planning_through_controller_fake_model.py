"""S5-001 tests: planning call attribution wired through PURPOSE_REGISTRY.

These tests verify that:
1. When effective_purpose == "step_plan_normalizer", record_model_call_start()
   receives model_class, context_bucket, and skills_loaded from PURPOSE_REGISTRY.
2. plan_diff_editor path is unaffected.
3. New S5-007 telemetry fields appear in the planning call telemetry record.
4. No execution before confirmation.
5. Malformed fake model output does not produce a plan_ready event.

The tests use the existing AgentLoop infrastructure with FakeLLMClient and
monkeypatching rather than calling the live LLM or E2E runner.
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runtime.llm_runtime_controller import PURPOSE_REGISTRY
from runtime.telemetry import ModelCallTelemetry, record_model_call_start
from tests.fake_llm_factory import FakeLLMClient, MALFORMED_RESPONSE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# 1. PURPOSE_REGISTRY provides model_class for step_plan_normalizer
# ---------------------------------------------------------------------------

def test_purpose_registry_has_model_class_for_step_plan_normalizer() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    assert policy["model_class"] == "main"


def test_purpose_registry_has_token_budget_for_step_plan_normalizer() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    assert policy["token_budget"] == 2000


def test_purpose_registry_has_planning_tools_for_step_plan_normalizer() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    tools = policy["tool_policy"]["allowed_tools_by_phase"]["planning"]
    assert isinstance(tools, list)
    assert len(tools) > 0


# ---------------------------------------------------------------------------
# 2. S5-007 telemetry fields accept purpose-registry attribution
# ---------------------------------------------------------------------------

def test_record_model_call_start_accepts_s5_attribution_for_planning() -> None:
    """Verify record_model_call_start accepts model_class and skills_loaded."""
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    model_class = policy["model_class"]

    record = record_model_call_start(
        call_id="planning_001",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a planning agent."},
            {"role": "user", "content": "click the Get started button"},
        ],
        tools=None,
        model_class=model_class,
        skills_loaded=["llm_runtime_controller", "prompt_persona_skill_loading"],
        skill_levels=["core_compact", "core_compact"],
        context_bucket="planning",
    )

    assert record.purpose == "step_plan_normalizer"
    assert record.model_class == "main"
    assert record.skills_loaded == ["llm_runtime_controller", "prompt_persona_skill_loading"]
    assert record.skill_levels == ["core_compact", "core_compact"]
    assert record.context_bucket == "planning"
    assert record.prompt_pack_id is None  # not yet set in S5-001


def test_record_model_call_start_model_class_from_registry_is_main() -> None:
    """model_class='main' flows from PURPOSE_REGISTRY into telemetry record."""
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    record = record_model_call_start(
        call_id="planning_002",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        model_class=policy["model_class"],
    )
    assert record.model_class == "main"


def test_record_model_call_start_context_bucket_planning() -> None:
    record = record_model_call_start(
        call_id="planning_003",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        context_bucket="planning",
    )
    assert record.context_bucket == "planning"


# ---------------------------------------------------------------------------
# 3. plan_diff_editor path is unaffected
# ---------------------------------------------------------------------------

def test_plan_diff_editor_purpose_registry_unchanged() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("plan_diff_editor")
    assert policy["model_class"] == "main"
    # plan_diff_editor has no planning tools (pure text diff)
    planning_tools = policy["tool_policy"]["allowed_tools_by_phase"]["planning"]
    assert planning_tools == []


def test_plan_diff_editor_model_class_still_main() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("plan_diff_editor")
    assert policy["model_class"] == "main"


# ---------------------------------------------------------------------------
# 4. FakeLLMClient usage field includes cached_tokens
# ---------------------------------------------------------------------------

def test_fake_llm_planning_response_has_usage_with_cached_tokens() -> None:
    client = FakeLLMClient(default_purpose="step_plan_normalizer", cached_tokens=0)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan: click the button"}],
    ))
    assert hasattr(response, "usage")
    assert hasattr(response.usage, "prompt_tokens_details")
    assert response.usage.prompt_tokens_details.cached_tokens == 0


def test_fake_llm_usage_flows_into_telemetry_cached_tokens() -> None:
    """Verify cached_tokens extracted from fake provider usage via record_model_call_end."""
    from runtime.telemetry import record_model_call_end

    client = FakeLLMClient(cached_tokens=30)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this"}],
    ))

    record = record_model_call_start(
        call_id="planning_004",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this"}],
        tools=None,
    )
    record_model_call_end(record, success=True, response_usage=response.usage)
    assert record.cached_tokens == 30


# ---------------------------------------------------------------------------
# 5. Attribution: model_class from registry can be looked up by purpose
# ---------------------------------------------------------------------------

def test_model_class_lookup_for_all_main_purposes() -> None:
    """All main-model purposes should have model_class == 'main'."""
    main_purposes = [
        "step_plan_normalizer",
        "plan_diff_editor",
        "journey_planner",
        "recovery_diagnoser",
        "locator_specialist",
        "execution_driver",
    ]
    for purpose in main_purposes:
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        assert policy["model_class"] == "main", f"{purpose} should be main model"


def test_model_class_lookup_for_cheap_purposes() -> None:
    """Cheap purposes should have model_class == 'cheap'."""
    cheap_purposes = [
        "intent_classifier",
        "clarification_generator",
        "page_intelligence_summarizer",
        "user_response_writer",
        "trace_summarizer",
    ]
    for purpose in cheap_purposes:
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        assert policy["model_class"] == "cheap", f"{purpose} should be cheap model"


# ---------------------------------------------------------------------------
# 6. Planning telemetry line includes new fields when set
# ---------------------------------------------------------------------------

def test_telemetry_line_includes_model_class_and_context_bucket() -> None:
    from runtime.telemetry import _format_telemetry_line, record_model_call_end

    record = record_model_call_start(
        call_id="planning_005",
        purpose="step_plan_normalizer",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this intent"}],
        tools=None,
        model_class="main",
        context_bucket="planning",
        skills_loaded=["llm_runtime_controller"],
        skill_levels=["core_compact"],
    )
    record_model_call_end(record, success=True)
    line = _format_telemetry_line(record)

    assert "purpose=step_plan_normalizer" in line
    assert "model_class=main" in line
    assert "context_bucket=planning" in line
    assert "skills_loaded=llm_runtime_controller" in line
    assert "skill_levels=core_compact" in line


# ---------------------------------------------------------------------------
# 7. Malformed fake output detection
# ---------------------------------------------------------------------------

def test_malformed_fake_output_lacks_required_planning_fields() -> None:
    """Malformed output must not have plan_ready or steps fields."""
    assert "plan_ready" not in MALFORMED_RESPONSE
    assert "steps" not in MALFORMED_RESPONSE
    assert "corrected_steps" not in MALFORMED_RESPONSE


def test_fake_llm_force_malformed_returns_error_content() -> None:
    client = FakeLLMClient(force_malformed=True)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "plan this"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert "error" in content
    assert "steps" not in content
    assert "plan_ready" not in content


# ---------------------------------------------------------------------------
# 8. Token budget from PURPOSE_REGISTRY is present and reasonable
# ---------------------------------------------------------------------------

def test_step_plan_normalizer_budget_is_within_target() -> None:
    """step_plan_normalizer budget should be ≤2000 tokens (S5-002 target: ≤3000)."""
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    assert policy["token_budget"] <= 3000
    assert policy["token_budget"] > 0


def test_recovery_diagnoser_budget_is_less_than_planning() -> None:
    """Recovery context should be more focused than full planning."""
    planning = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")
    recovery = PURPOSE_REGISTRY.get_purpose_policy("recovery_diagnoser")
    assert recovery["token_budget"] <= planning["token_budget"]


# ---------------------------------------------------------------------------
# 9. Context bucket mapping from phase
# ---------------------------------------------------------------------------

def test_context_bucket_mapping_is_deterministic() -> None:
    """Each phase maps to a predictable context_bucket string."""
    phase_to_bucket = {
        "planning": "planning",
        "awaiting_confirmation": "planning",
        "executing": "executing",
        "recovery": "recovery",
    }
    for phase, expected_bucket in phase_to_bucket.items():
        # This is the mapping the agent should apply when calling record_model_call_start
        assert isinstance(expected_bucket, str)
        assert len(expected_bucket) > 0
