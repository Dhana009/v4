from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class ToolDispatcher:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def dispatch(self, tool_name: str, args: Any) -> dict[str, Any]:
        return await self._loop._dispatch_tool(tool_name, args)

    def parse_tool_args(self, raw_args: Any) -> dict[str, Any]:
        return self._loop._parse_tool_args(raw_args)

    def normalize_wait_until(self, value: Any) -> Any:
        return self._loop._normalize_wait_until(value)

    def is_browser_state_tool(self, tool_name: str) -> bool:
        return self._loop._is_browser_state_tool(tool_name)

    def append_tool_response(self, tool_call_id: str, result: Any) -> None:
        return self._loop._append_tool_response(tool_call_id, result)

    def append_skipped_tool_response(self, tool_call_id: str, reason: str) -> None:
        return self._loop._append_skipped_tool_response(tool_call_id, reason)

    def append_skipped_tool_responses(self, tool_calls: list[Any], start_index: int, reason: str) -> None:
        return self._loop._append_skipped_tool_responses(tool_calls, start_index, reason)
