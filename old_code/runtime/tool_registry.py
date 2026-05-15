from __future__ import annotations

import copy
from dataclasses import dataclass
import json
from typing import Any

from runtime.telemetry import estimate_text_tokens

PLANNING_SAFE_TOOL_NAMES = {
    "send_to_overlay",
    "browser_get_state",
    "dom_extract",
    "locator_find",
    "locator_validate",
    "ask_user",
}

RECORDING_WAIT_SAFE_TOOL_NAMES = {
    "send_to_overlay",
    "ask_user",
}


@dataclass(slots=True)
class ToolDiagnostics:
    tool_count: int
    tool_names: list[str]
    estimated_total_tool_tokens: int
    per_tool_estimated_tokens: dict[str, int]
    largest_tool_name: str
    largest_tool_tokens: int
    suggested_future_policy: str


def _normalize_tools(tools: Any) -> list[Any]:
    if tools is None:
        return []
    if isinstance(tools, (list, tuple)):
        return list(tools)
    return [tools]


def _tool_name(tool: Any, index: int) -> str:
    if isinstance(tool, dict):
        function = tool.get("function")
        if isinstance(function, dict):
            name = function.get("name")
            if name:
                return str(name)
    return f"tool_{index + 1}"


def strip_llm_thinking_from_send_to_overlay(tools: list[Any]) -> list[Any]:
    """Return a copy of tools where send_to_overlay's message_type enum excludes llm_thinking.

    Called after convergence narrowing so the schema itself forbids the model from
    choosing llm_thinking again — natural language instructions alone are insufficient.
    """
    result = []
    for tool in tools:
        if not isinstance(tool, dict) or tool.get("function", {}).get("name") != "send_to_overlay":
            result.append(tool)
            continue
        tool_copy = copy.deepcopy(tool)
        fn = tool_copy["function"]
        mt = fn.get("parameters", {}).get("properties", {}).get("message_type", {})
        mt["enum"] = [v for v in mt.get("enum", []) if v != "llm_thinking"]
        fn["description"] = (
            "Send a structured message to the browser overlay panel. "
            "Use message_type='plan_ready' to submit your final plan proposal and exit planning — "
            "this is the required terminal call for step_plan_normalizer. "
            "llm_thinking is not permitted at this stage. You MUST call plan_ready or ask_user now."
        )
        result.append(tool_copy)
    return result


def filter_tools_for_recording_wait(tools: Any) -> list[Any]:
    normalized_tools = _normalize_tools(tools)
    original_count = len(normalized_tools)
    filtered_tools = [
        tool
        for index, tool in enumerate(normalized_tools)
        if _tool_name(tool, index) in RECORDING_WAIT_SAFE_TOOL_NAMES
    ]
    filtered_count = len(filtered_tools)
    print(
        "[TOOL_FILTER] "
        "phase=recording "
        "awaiting_step_record=true "
        f"original={original_count} "
        f"filtered={filtered_count} "
        f"removed={original_count - filtered_count}"
    )
    return filtered_tools


def filter_tools_for_phase(
    tools: Any,
    phase: str,
    awaiting_step_record: bool = False,
    correction_mode: dict[str, Any] | None = None,
    allowed_tool_names: set[str] | tuple[str, ...] | list[str] | None = None,
) -> list[Any]:
    normalized_tools = _normalize_tools(tools)
    normalized_phase = str(phase or "").strip().lower()
    original_count = len(normalized_tools)
    has_allowed_tool_names = allowed_tool_names is not None
    normalized_allowed_tool_names = {
        str(name).strip()
        for name in (allowed_tool_names or ())
        if str(name).strip()
    }

    if normalized_phase == "recording" and awaiting_step_record:
        filtered_tools = filter_tools_for_recording_wait(normalized_tools)
        if has_allowed_tool_names:
            filtered_tools = [
                tool
                for index, tool in enumerate(filtered_tools)
                if _tool_name(tool, index) in normalized_allowed_tool_names
            ]
        return filtered_tools

    correction_category = ""
    correction_needs_clarification = False
    if isinstance(correction_mode, dict):
        correction_category = str(correction_mode.get("category") or "").strip().lower()
        correction_needs_clarification = bool(correction_mode.get("needs_clarification"))

    if normalized_phase in {"planning", "awaiting_confirmation"} and correction_category:
        if correction_needs_clarification or correction_category == "ambiguous":
            allowed_tool_names = {"ask_user"}
        else:
            allowed_tool_names = {"send_to_overlay"}
        filtered_tools = [
            tool
            for index, tool in enumerate(normalized_tools)
            if _tool_name(tool, index) in allowed_tool_names
        ]
        filtered_count = len(filtered_tools)
        print(
            "[TOOL_FILTER] "
            f"phase={normalized_phase or 'unknown'} "
            f"correction_mode={correction_category or 'unknown'} "
            f"original={original_count} "
            f"filtered={filtered_count} "
            f"removed={original_count - filtered_count}"
        )
        return filtered_tools

    if normalized_phase in {"executing", "recording", "recovery", "recovering"}:
        filtered_tools = list(normalized_tools)
    else:
        filtered_tools = [
            tool
            for index, tool in enumerate(normalized_tools)
            if _tool_name(tool, index) in PLANNING_SAFE_TOOL_NAMES
        ]
        if normalized_phase not in {"planning", "awaiting_confirmation"}:
            print(
                "[TOOL_FILTER] "
                f"warning=unknown_phase phase={normalized_phase or 'unknown'}"
            )

    if has_allowed_tool_names:
        filtered_tools = [
            tool
            for index, tool in enumerate(filtered_tools)
            if _tool_name(tool, index) in normalized_allowed_tool_names
        ]

    filtered_count = len(filtered_tools)
    print(
        "[TOOL_FILTER] "
        f"phase={normalized_phase or 'unknown'} "
        f"original={original_count} "
        f"filtered={filtered_count} "
        f"removed={original_count - filtered_count}"
    )
    return filtered_tools


class ToolRegistry:
    def analyze(self, tools: Any) -> ToolDiagnostics:
        if tools is None:
            normalized_tools: list[Any] = []
        elif isinstance(tools, (list, tuple)):
            normalized_tools = list(tools)
        else:
            normalized_tools = [tools]

        tool_names: list[str] = []
        per_tool_estimated_tokens: dict[str, int] = {}
        estimated_total_tool_tokens = 0
        largest_tool_name = "none"
        largest_tool_tokens = 0

        for index, tool in enumerate(normalized_tools):
            tool_name = self._extract_tool_name(tool, index)
            serialized_tool = self._serialize_tool(tool)
            token_count = estimate_text_tokens(serialized_tool)

            tool_names.append(tool_name)
            per_tool_estimated_tokens[tool_name] = token_count
            estimated_total_tool_tokens += token_count

            if token_count > largest_tool_tokens:
                largest_tool_name = tool_name
                largest_tool_tokens = token_count

        return ToolDiagnostics(
            tool_count=len(normalized_tools),
            tool_names=tool_names,
            estimated_total_tool_tokens=estimated_total_tool_tokens,
            per_tool_estimated_tokens=per_tool_estimated_tokens,
            largest_tool_name=largest_tool_name,
            largest_tool_tokens=largest_tool_tokens,
            suggested_future_policy=self._suggested_future_policy(estimated_total_tool_tokens),
        )

    def _extract_tool_name(self, tool: Any, index: int) -> str:
        return _tool_name(tool, index)

    def _serialize_tool(self, tool: Any) -> str:
        if isinstance(tool, dict):
            try:
                return json.dumps(tool, ensure_ascii=True, separators=(",", ":"))
            except Exception:  # noqa: BLE001
                return str(tool)
        return str(tool)

    def _suggested_future_policy(self, estimated_total_tool_tokens: int) -> str:
        if estimated_total_tool_tokens > 3000:
            return "needs_progressive_tools"
        if estimated_total_tool_tokens >= 1200:
            return "consider_tool_groups"
        return "ok_current"
