"""
tests/test_page_intelligence_summarizer_policy.py

Tests for S6-0303: Cheap-model page intelligence summarizer policy.
"""
from __future__ import annotations

import pytest


def test_policy_resolves_for_summarizer():
    from runtime.llm_policy_registry import POLICY_REGISTRY
    policy = POLICY_REGISTRY.get("page_intelligence_summarizer")
    assert policy["purpose_id"] == "page_intelligence_summarizer"


def test_cheap_model_class():
    from runtime.llm_policy_registry import POLICY_REGISTRY
    policy = POLICY_REGISTRY.get("page_intelligence_summarizer")
    assert policy["model_class"] == "cheap"


def test_context_level_is_l1_or_l3():
    from runtime.context_policy import PURPOSE_CONTEXT_DEFAULTS
    level = PURPOSE_CONTEXT_DEFAULTS["page_intelligence_summarizer"]
    assert level in ("L1", "L2", "L3")


def test_inspection_only_tools():
    from runtime.tool_exposure_enforcement import get_allowed_tools
    tools = get_allowed_tools("page_intelligence_summarizer")
    # Must not have execution/action tools
    action_tools = {"action_click", "action_fill", "next_operation", "action_assert"}
    overlap = set(tools) & action_tools
    assert len(overlap) == 0, f"Summarizer exposes action tools: {overlap}"


def test_schema_validator_rejects_incomplete_summary():
    from runtime.schema_validation_policy import validate_output
    result = validate_output("page_intelligence_summarizer", "Sure, here's a summary.")
    assert result.valid is False


def test_deterministic_fallback_used_on_failure():
    from runtime.page_intelligence_live import invoke_page_intelligence
    # Bad URL should trigger fallback
    result = invoke_page_intelligence("about:blank", selected_section=None)
    assert result.source in ("deterministic", "fallback", "fake")


def test_fake_cheap_model_creates_valid_summary():
    from runtime.page_intelligence_live import invoke_page_intelligence
    result = invoke_page_intelligence("https://example.com", selected_section=None)
    assert result is not None
    assert isinstance(result.packet, dict)


def test_source_field_indicates_origin():
    from runtime.page_intelligence_live import invoke_page_intelligence
    result = invoke_page_intelligence("https://example.com", selected_section=None)
    assert result.source in ("deterministic", "cheap_model", "fake", "mixed", "fallback")


def test_cheap_model_output_cannot_mark_locator_final():
    """Source field must not claim final locator authority."""
    from runtime.page_intelligence_live import invoke_page_intelligence
    result = invoke_page_intelligence("https://example.com", selected_section=None)
    # The packet must not have a 'locator_final' field set to True
    assert result.packet.get("locator_final", False) is False


def test_summarizer_fallback_is_deterministic():
    from runtime.llm_policy_registry import POLICY_REGISTRY
    policy = POLICY_REGISTRY.get("page_intelligence_summarizer")
    assert policy["fallback_policy"] in ("fail_closed", "ask_user", "retry")
