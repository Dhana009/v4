from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class ToolDefinitions:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def build(self) -> list[dict[str, Any]]:
        return self._loop._build_tool_definitions()
