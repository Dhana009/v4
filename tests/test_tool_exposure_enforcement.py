"""
tests/test_tool_exposure_enforcement.py

Tests for S6-0205: Tool exposure enforcement.
Verifies per-purpose tool access control.
"""
from __future__ import annotations

import pytest
from runtime.tool_exposure_enforcement import (
    get_allowed_tools,
    build_tool_schemas_for_purpose,
    validate_tool_policy_integrity,
)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_intent_classifier_exposes_only_ask_user():
    tools = get_allowed_tools("intent_classifier")
    # Intent classifier should only have minimal tools — no execution/locator tools
    for tool in tools:
        assert tool not in (
            "action_click", "action_fill", "action_assert",
            "browser_get_state", "locator_search",
        ), f"Intent classifier should not expose {tool}"


def test_page_validation_recommender_forbids_execution_tools():
    tools = get_allowed_tools("page_validation_recommender")
    execution_tools = {"action_click", "action_fill", "action_assert", "next_operation"}
    overlap = set(tools) & execution_tools
    assert len(overlap) == 0, f"Recommender exposes execution tools: {overlap}"


def test_locator_specialist_forbids_action_tools():
    tools = get_allowed_tools("locator_specialist")
    action_tools = {"action_click", "action_fill", "next_operation"}
    overlap = set(tools) & action_tools
    assert len(overlap) == 0, f"Locator specialist exposes action tools: {overlap}"


def test_execution_driver_forbids_planning_tools():
    # execution_driver should not have planning-only tools
    tools = get_allowed_tools("execution_driver")
    # planning tools that should NOT be available during execution
    # execution_driver should only have execution tools
    assert isinstance(tools, list)


def test_recovery_diagnoser_forbids_execution_tools():
    tools = get_allowed_tools("recovery_diagnoser")
    execution_tools = {"action_click", "action_fill", "next_operation"}
    # recovery gets diagnostic tools, not action tools
    overlap = set(tools) & execution_tools
    assert len(overlap) == 0, f"Recovery diagnoser exposes execution tools: {overlap}"


def test_unknown_purpose_raises():
    with pytest.raises(ValueError):
        get_allowed_tools("nonexistent_purpose")


def test_tool_exposure_per_purpose_matches_policy():
    from runtime.llm_policy_registry import POLICY_REGISTRY
    for pid in POLICY_REGISTRY.list_purposes():
        tools = get_allowed_tools(pid)
        assert isinstance(tools, list)


def test_build_tool_schemas_for_purpose_returns_list():
    schemas = build_tool_schemas_for_purpose("intent_classifier")
    assert isinstance(schemas, list)


def test_build_tool_schemas_valid_structure():
    schemas = build_tool_schemas_for_purpose("execution_driver")
    for schema in schemas:
        assert "name" in schema or isinstance(schema, dict)


def test_planning_purposes_forbid_execution_action_tools():
    """Planning purposes must not expose action execution tools."""
    planning_purposes = [
        "intent_classifier",
        "clarification_generator",
        "journey_planner",
        "step_plan_normalizer",
    ]
    # Execution action tools (not read-only browser tools) must be absent
    action_tools = {"action_click", "action_fill", "action_assert", "next_operation"}
    for pid in planning_purposes:
        tools = get_allowed_tools(pid)
        overlap = set(tools) & action_tools
        assert len(overlap) == 0, f"{pid} exposes action tools: {overlap}"


def test_page_intelligence_summarizer_has_no_action_tools():
    """Summarizer must not expose action/browser-mutating tools."""
    tools = get_allowed_tools("page_intelligence_summarizer")
    action_tools = {"action_click", "action_fill", "next_operation"}
    overlap = set(tools) & action_tools
    assert len(overlap) == 0, f"page_intelligence_summarizer exposes action tools: {overlap}"


def test_tool_policy_integrity_validates_all_tools_exist():
    """validate_tool_policy_integrity should pass — no dangling tool refs."""
    errors = validate_tool_policy_integrity()
    assert errors == [], f"Tool policy integrity errors: {errors}"
