from __future__ import annotations

from runtime.llm_runtime_controller import PURPOSE_REGISTRY
from runtime.tool_registry import ToolRegistry, filter_tools_for_phase


def _tool(name: str) -> dict[str, object]:
    return {"type": "function", "function": {"name": name}}


def _tool_names(tools: list[dict[str, object]]) -> list[str]:
    return [str(tool["function"]["name"]) for tool in tools]


def _build_tools() -> list[dict[str, object]]:
    return [
        _tool("action_click"),
        _tool("send_to_overlay"),
        _tool("locator_find"),
        _tool("page_navigate"),
        _tool("locator_validate"),
        _tool("dom_extract"),
        _tool("action_fill"),
        _tool("ask_user"),
        _tool("browser_get_state"),
        _tool("action_assert"),
    ]


def test_plan_diff_editor_returns_zero_tool_schema_by_default() -> None:
    tools = _build_tools()
    policy = PURPOSE_REGISTRY.get_purpose_policy("plan_diff_editor")

    filtered = filter_tools_for_phase(
        tools,
        "planning",
        allowed_tool_names=set(policy["tool_policy"]["allowed_tools_by_phase"]["planning"]),
    )

    assert filtered == []


def test_recovery_diagnoser_returns_only_recovery_tools() -> None:
    tools = _build_tools()
    policy = PURPOSE_REGISTRY.get_purpose_policy("recovery_diagnoser")

    filtered = filter_tools_for_phase(
        tools,
        "recovery",
        allowed_tool_names=set(policy["tool_policy"]["allowed_tools_by_phase"]["planning"]),
    )

    assert _tool_names(filtered) == ["ask_user", "browser_get_state"]


def test_page_intelligence_summarizer_returns_dom_extract_only() -> None:
    tools = _build_tools()
    policy = PURPOSE_REGISTRY.get_purpose_policy("page_intelligence_summarizer")

    filtered = filter_tools_for_phase(
        tools,
        "planning",
        allowed_tool_names=set(policy["tool_policy"]["allowed_tools_by_phase"]["planning"]),
    )

    assert _tool_names(filtered) == ["dom_extract"]


def test_step_plan_normalizer_uses_planning_safe_tools_without_execution_tools() -> None:
    tools = _build_tools()
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")

    filtered = filter_tools_for_phase(
        tools,
        "planning",
        allowed_tool_names=set(policy["tool_policy"]["allowed_tools_by_phase"]["planning"]),
    )

    assert _tool_names(filtered) == [
        "send_to_overlay",
        "locator_find",
        "locator_validate",
        "dom_extract",
        "ask_user",
        "browser_get_state",
    ]


def test_filtered_tool_schema_token_estimate_is_smaller_than_full_schema() -> None:
    tools = _build_tools()
    policy = PURPOSE_REGISTRY.get_purpose_policy("page_intelligence_summarizer")
    registry = ToolRegistry()

    filtered = filter_tools_for_phase(
        tools,
        "planning",
        allowed_tool_names=set(policy["tool_policy"]["allowed_tools_by_phase"]["planning"]),
    )

    full_tokens = registry.analyze(tools).estimated_total_tool_tokens
    filtered_tokens = registry.analyze(filtered).estimated_total_tool_tokens

    assert filtered_tokens < full_tokens
