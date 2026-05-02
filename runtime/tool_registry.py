from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from runtime.telemetry import estimate_text_tokens


@dataclass(slots=True)
class ToolDiagnostics:
    tool_count: int
    tool_names: list[str]
    estimated_total_tool_tokens: int
    per_tool_estimated_tokens: dict[str, int]
    largest_tool_name: str
    largest_tool_tokens: int
    suggested_future_policy: str


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
        if isinstance(tool, dict):
            function = tool.get("function")
            if isinstance(function, dict):
                name = function.get("name")
                if name:
                    return str(name)
        return f"tool_{index + 1}"

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
