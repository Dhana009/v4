"""BUG-S5-013-007: Tool schema clarity contract tests.

Tests that the tool descriptions for send_to_overlay (plan_ready), ask_user,
and send_to_overlay (llm_thinking) contain the required terminal/non-terminal
contract text that guides the model to converge correctly.
"""
from __future__ import annotations

from llm.tool_definitions import ToolDefinitions
from types import SimpleNamespace


def _get_tool_definitions() -> list[dict]:
    # ToolDefinitions requires an AgentLoop but only uses it lazily; we can
    # pass a minimal stub for the purposes of reading the schema text.
    stub_loop = SimpleNamespace()
    td = ToolDefinitions(loop=stub_loop)
    return td.build()


def _find_tool(tools: list[dict], name: str) -> dict | None:
    for t in tools:
        if t.get("function", {}).get("name") == name:
            return t
    return None


# ---------------------------------------------------------------------------
# Test 1: send_to_overlay description makes plan_ready clearly terminal
# ---------------------------------------------------------------------------

def test_send_to_overlay_schema_makes_plan_ready_terminal() -> None:
    """The send_to_overlay tool description must clearly state that plan_ready
    is the terminal call for planning — not just another message type option.
    """
    tools = _get_tool_definitions()
    overlay = _find_tool(tools, "send_to_overlay")
    assert overlay is not None, "send_to_overlay tool must exist"

    description = overlay["function"]["description"]

    assert "plan_ready" in description, (
        "send_to_overlay description must mention plan_ready"
    )
    assert "terminal" in description.lower(), (
        "send_to_overlay description must state plan_ready is terminal for planning"
    )
    # Must not mislead the model into thinking plan_ready is just a status message
    assert "status message" not in description.lower() or "terminal" in description.lower(), (
        "send_to_overlay must clarify plan_ready as terminal exit, not a status message"
    )


# ---------------------------------------------------------------------------
# Test 2: ask_user description makes clarification clearly terminal
# ---------------------------------------------------------------------------

def test_ask_user_schema_makes_clarification_terminal() -> None:
    """The ask_user tool description must state it is the required terminal call
    when intent is ambiguous or target is unclear — discouraging continued DOM
    exploration after ambiguity is established.
    """
    tools = _get_tool_definitions()
    ask_user = _find_tool(tools, "ask_user")
    assert ask_user is not None, "ask_user tool must exist"

    description = ask_user["function"]["description"]

    # Must mention ambiguous/multiple targets
    assert any(word in description.lower() for word in ("ambiguous", "unclear", "multiple", "clarif")), (
        "ask_user description must mention when to use it (ambiguous intent / multiple targets)"
    )
    # Must mention it is terminal / required when data is missing
    assert any(phrase in description.lower() for phrase in ("terminal", "required", "must call", "cannot")), (
        "ask_user description must indicate it is required/terminal when clarification is needed"
    )
    assert "plain text" in description.lower(), (
        "ask_user description must forbid answering clarification as plain text"
    )


# ---------------------------------------------------------------------------
# Test 3: llm_thinking description is non-terminal and limited
# ---------------------------------------------------------------------------

def test_llm_thinking_schema_is_non_terminal_and_limited() -> None:
    """The send_to_overlay tool description for llm_thinking must state:
    - it is non-terminal (must be followed by plan_ready or ask_user)
    - it must not be repeated (at most once)
    """
    tools = _get_tool_definitions()
    overlay = _find_tool(tools, "send_to_overlay")
    assert overlay is not None, "send_to_overlay tool must exist"

    description = overlay["function"]["description"]

    # Must say llm_thinking is limited (once / at most once)
    assert any(phrase in description.lower() for phrase in ("at most once", "once", "must not be repeated", "only once")), (
        "send_to_overlay description must state llm_thinking can only be used at most once"
    )
    # Must say llm_thinking must be followed by plan_ready or ask_user
    assert any(phrase in description for phrase in ("follow", "MUST follow", "must follow")), (
        "send_to_overlay description must state llm_thinking must be followed by plan_ready or ask_user"
    )
