from __future__ import annotations

from copy import deepcopy

import pytest

from runtime.tool_registry import filter_tools_for_phase


def _tool(name: str) -> dict[str, object]:
    return {"type": "function", "function": {"name": name}}


def _tool_names(tools: list[dict[str, object]]) -> list[str]:
    names: list[str] = []
    for tool in tools:
        function = tool.get("function") if isinstance(tool, dict) else None
        name = function.get("name") if isinstance(function, dict) else ""
        names.append(str(name))
    return names


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


@pytest.mark.parametrize("phase", ["planning", "awaiting_confirmation"])
def test_planning_phases_filter_to_safe_tools_only(phase: str) -> None:
    tools = _build_tools()
    before = deepcopy(tools)

    filtered_tools = filter_tools_for_phase(tools, phase)

    assert filtered_tools is not tools
    assert _tool_names(filtered_tools) == [
        "send_to_overlay",
        "locator_find",
        "locator_validate",
        "dom_extract",
        "ask_user",
        "browser_get_state",
    ]
    assert tools == before


@pytest.mark.parametrize("phase", ["executing", "recording", "recovery"])
def test_runtime_phases_return_all_tools_in_original_order_without_mutation(phase: str) -> None:
    tools = _build_tools()
    before = deepcopy(tools)

    filtered_tools = filter_tools_for_phase(tools, phase)

    assert filtered_tools is not tools
    assert _tool_names(filtered_tools) == _tool_names(tools)
    assert filtered_tools == tools
    assert tools == before


def test_unknown_phase_falls_back_to_safe_tools_and_logs_warning(capsys: pytest.CaptureFixture[str]) -> None:
    tools = _build_tools()

    filtered_tools = filter_tools_for_phase(tools, "mystery")

    captured = capsys.readouterr().out
    assert _tool_names(filtered_tools) == [
        "send_to_overlay",
        "locator_find",
        "locator_validate",
        "dom_extract",
        "ask_user",
        "browser_get_state",
    ]
    assert "[TOOL_FILTER] warning=unknown_phase phase=mystery" in captured
    assert "[TOOL_FILTER] phase=mystery original=10 filtered=6 removed=4" in captured
