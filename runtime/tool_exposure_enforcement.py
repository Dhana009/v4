"""
runtime/tool_exposure_enforcement.py

Runtime enforcement of per-purpose tool exposure matrix.

Source rule: Runtime Policy Spec — tool exposure enforced at runtime per purpose.
LLM cannot access tools not in purpose policy. Unknown purpose → zero tools.
Planning purposes have zero action/browser tools.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from typing import Any

from runtime.tool_schema_policy import PURPOSE_PLANNING_TOOL_NAMES


# ---------------------------------------------------------------------------
# Canonical set of all known tools
# ---------------------------------------------------------------------------

ALL_KNOWN_TOOLS: frozenset[str] = frozenset({
    # Planning / inspection tools
    "ask_user",
    "needs_more_context",
    "send_to_overlay",
    "dom_extract",
    "browser_get_state",
    # Locator tools
    "locator_find",
    "locator_validate",
    "locator_search",
    # Execution tools
    "next_operation",
    "action_click",
    "action_fill",
    "action_assert",
    # Recovery / diagnostic tools
    "diagnostic_tools",
    # Step planning tools (from PLANNING_SAFE_TOOL_NAMES in tool_registry)
    "step_add",
    "step_remove",
    "step_reorder",
    "step_update",
    "step_validate",
    "step_finalize",
})

# Execution tools that planning purposes must never expose
_EXECUTION_TOOLS: frozenset[str] = frozenset({
    "next_operation", "action_click", "action_fill", "action_assert",
})

# Browser tools that planning purposes must never expose
_BROWSER_TOOLS: frozenset[str] = frozenset({
    "browser_get_state",
})


# ---------------------------------------------------------------------------
# Tool exposure per purpose
# ---------------------------------------------------------------------------

# Maps purpose → allowed tool names list (enforced at runtime)
PURPOSE_TOOL_EXPOSURE: dict[str, list[str]] = {}

for _pid, _tools in PURPOSE_PLANNING_TOOL_NAMES.items():
    PURPOSE_TOOL_EXPOSURE[_pid] = list(_tools)

# Execution driver gets its execution tools (from policy registry)
PURPOSE_TOOL_EXPOSURE["execution_driver"] = ["next_operation", "action_click", "action_fill", "action_assert", "ask_user"]
# Recovery purposes get diagnostic + ask_user
PURPOSE_TOOL_EXPOSURE["recovery_diagnoser"] = ["browser_get_state", "ask_user"]
PURPOSE_TOOL_EXPOSURE["replay_repair_specialist"] = ["browser_get_state", "ask_user"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_allowed_tools(purpose_id: str) -> list[str]:
    """Return the list of tool names allowed for *purpose_id*.

    Raises ValueError for unknown purposes.
    """
    from runtime.llm_purpose_policy import REQUIRED_PURPOSE_IDS
    if purpose_id not in REQUIRED_PURPOSE_IDS:
        raise ValueError(f"Unknown purpose: {purpose_id!r}")
    return list(PURPOSE_TOOL_EXPOSURE.get(purpose_id, []))


def build_tool_schemas_for_purpose(purpose_id: str) -> list[dict[str, Any]]:
    """Return tool schema dicts for *purpose_id*.

    Builds minimal schema stubs for each allowed tool.
    Raises ValueError for unknown purposes.
    """
    allowed = get_allowed_tools(purpose_id)
    schemas: list[dict[str, Any]] = []
    for tool_name in allowed:
        schemas.append({
            "name": tool_name,
            "description": f"Tool: {tool_name}",
            "parameters": {"type": "object", "properties": {}},
        })
    return schemas


def validate_tool_policy_integrity() -> list[str]:
    """Check that every tool in PURPOSE_TOOL_EXPOSURE is in ALL_KNOWN_TOOLS.

    Returns list of error strings. Empty list means integrity is intact.
    """
    errors: list[str] = []
    for purpose, tools in PURPOSE_TOOL_EXPOSURE.items():
        for tool in tools:
            if tool not in ALL_KNOWN_TOOLS:
                errors.append(f"Purpose {purpose!r} references unknown tool {tool!r}")
    return errors
