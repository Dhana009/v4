"""S5-012: Tests for FakeLLMClient and default stub responses."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from tests.fake_llm_factory import (
    FakeLLMClient,
    DEFAULT_STEP_PLAN_NORMALIZER_RESPONSE,
    DEFAULT_PLAN_DIFF_EDITOR_RESPONSE,
    DEFAULT_RECOVERY_DIAGNOSER_RESPONSE,
    DEFAULT_PAGE_INTELLIGENCE_RESPONSE,
    DEFAULT_LOCATOR_SPECIALIST_RESPONSE,
    MALFORMED_RESPONSE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _call_with_purpose_hint(client: FakeLLMClient, purpose: str) -> Any:
    """Call the fake client with a message that hints the purpose."""
    return _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are running as {purpose}."},
            {"role": "user", "content": f"Execute {purpose} task."},
        ],
    ))


# ---------------------------------------------------------------------------
# Call capture
# ---------------------------------------------------------------------------

def test_fake_llm_captures_call_payload() -> None:
    client = FakeLLMClient()
    _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hello"}],
    ))
    assert client.get_call_count() == 1
    last = client.get_last_call()
    assert last is not None
    assert last["model"] == "gpt-4o-mini"
    assert last["messages"][0]["content"] == "hello"


def test_fake_llm_captures_multiple_calls() -> None:
    client = FakeLLMClient()
    for i in range(3):
        _run(client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"call {i}"}],
        ))
    assert client.get_call_count() == 3
    assert client.get_messages_for_call(0)[0]["content"] == "call 0"
    assert client.get_messages_for_call(2)[0]["content"] == "call 2"


# ---------------------------------------------------------------------------
# step_plan_normalizer stub
# ---------------------------------------------------------------------------

def test_fake_llm_returns_step_plan_normalizer_response() -> None:
    client = FakeLLMClient(default_purpose="step_plan_normalizer")
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "click the button"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert content["purpose"] == "step_plan_normalizer"
    assert isinstance(content["steps"], list)
    assert len(content["steps"]) > 0
    step = content["steps"][0]
    assert "step_id" in step
    assert "intent" in step
    assert isinstance(step["children"], list)
    assert content["plan_ready"] is True
    assert content["requires_confirmation"] is True


def test_step_plan_normalizer_has_valid_children() -> None:
    stub = DEFAULT_STEP_PLAN_NORMALIZER_RESPONSE
    child = stub["steps"][0]["children"][0]
    assert "operation_id" in child
    assert child["type"] in ("click", "fill", "assert_visible", "assert_text")
    assert "target" in child
    assert "locator" in child


# ---------------------------------------------------------------------------
# plan_diff_editor stub
# ---------------------------------------------------------------------------

def test_fake_llm_returns_plan_diff_editor_response() -> None:
    client = FakeLLMClient(default_purpose="plan_diff_editor")
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "assert first then click"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert content["purpose"] == "plan_diff_editor"
    assert isinstance(content["corrected_steps"], list)
    assert content["correction_applied"] is True
    assert content["requires_confirmation"] is True


def test_plan_diff_editor_preserves_step_ids() -> None:
    stub = DEFAULT_PLAN_DIFF_EDITOR_RESPONSE
    assert stub["corrected_steps"][0]["step_id"] == "pending-step-1"


# ---------------------------------------------------------------------------
# recovery_diagnoser stub
# ---------------------------------------------------------------------------

def test_fake_llm_returns_recovery_diagnoser_response() -> None:
    client = FakeLLMClient(default_purpose="recovery_diagnoser")
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "step failed with timeout"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert content["purpose"] == "recovery_diagnoser"
    assert content["recovery_action"] in ("retry", "ask_user", "skip", "stop")
    assert "reason" in content
    assert "confidence" in content


def test_recovery_diagnoser_has_proposed_locator() -> None:
    stub = DEFAULT_RECOVERY_DIAGNOSER_RESPONSE
    assert "proposed_locator" in stub
    assert isinstance(stub["proposed_locator"], str)


# ---------------------------------------------------------------------------
# usage / cached_tokens
# ---------------------------------------------------------------------------

def test_fake_llm_returns_usage_with_cached_tokens() -> None:
    client = FakeLLMClient(cached_tokens=50)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
    ))
    assert hasattr(response, "usage")
    assert hasattr(response.usage, "prompt_tokens")
    assert hasattr(response.usage, "completion_tokens")
    assert hasattr(response.usage, "total_tokens")
    assert hasattr(response.usage, "prompt_tokens_details")
    assert response.usage.prompt_tokens_details.cached_tokens == 50


def test_fake_llm_usage_tokens_sum_correctly() -> None:
    client = FakeLLMClient(prompt_tokens=120, cached_tokens=0)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "sum test"}],
    ))
    usage = response.usage
    assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens


def test_fake_llm_cached_tokens_zero_by_default() -> None:
    client = FakeLLMClient()
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
    ))
    assert response.usage.prompt_tokens_details.cached_tokens == 0


# ---------------------------------------------------------------------------
# Malformed output (negative tests)
# ---------------------------------------------------------------------------

def test_fake_llm_can_return_malformed_output() -> None:
    client = FakeLLMClient(force_malformed=True)
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert "error" in content
    assert content.get("missing_required_fields") is True
    # Must not have purpose-specific fields
    assert "steps" not in content
    assert "corrected_steps" not in content
    assert "recovery_action" not in content


def test_malformed_response_lacks_plan_ready() -> None:
    assert "plan_ready" not in MALFORMED_RESPONSE
    assert "steps" not in MALFORMED_RESPONSE


# ---------------------------------------------------------------------------
# Multiple purpose responses
# ---------------------------------------------------------------------------

def test_fake_llm_supports_custom_purpose_response() -> None:
    custom = {"purpose": "custom_purpose", "result": "custom_value"}
    client = FakeLLMClient(
        purpose_responses={"step_plan_normalizer": custom},
        default_purpose="step_plan_normalizer",
    )
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "click button"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert content["purpose"] == "custom_purpose"
    assert content["result"] == "custom_value"


def test_fake_llm_page_intelligence_response() -> None:
    client = FakeLLMClient(default_purpose="page_intelligence_summarizer")
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "analyze page DOM"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert content["purpose"] == "page_intelligence_summarizer"
    assert content["semantic_quality"] in ("good", "mixed", "poor")
    assert isinstance(content["elements"], list)


def test_fake_llm_locator_specialist_response() -> None:
    client = FakeLLMClient(default_purpose="locator_specialist")
    response = _run(client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "find locator for button"}],
    ))
    content = json.loads(response.choices[0].message.content)
    assert content["purpose"] == "locator_specialist"
    assert isinstance(content["candidates"], list)
    assert "recommended" in content
    assert content["requires_validation"] is True


# ---------------------------------------------------------------------------
# Schema structural invariants
# ---------------------------------------------------------------------------

def test_all_default_stubs_have_purpose_field() -> None:
    stubs = [
        DEFAULT_STEP_PLAN_NORMALIZER_RESPONSE,
        DEFAULT_PLAN_DIFF_EDITOR_RESPONSE,
        DEFAULT_RECOVERY_DIAGNOSER_RESPONSE,
        DEFAULT_PAGE_INTELLIGENCE_RESPONSE,
        DEFAULT_LOCATOR_SPECIALIST_RESPONSE,
    ]
    for stub in stubs:
        assert "purpose" in stub, f"Missing 'purpose' in stub: {stub}"


def test_fake_llm_response_is_json_serializable() -> None:
    client = FakeLLMClient()
    for purpose in ("step_plan_normalizer", "plan_diff_editor", "recovery_diagnoser"):
        client2 = FakeLLMClient(default_purpose=purpose)
        response = _run(client2.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
        ))
        # Must not raise
        parsed = json.loads(response.choices[0].message.content)
        assert isinstance(parsed, dict)
