from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class Codegen:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def locator_label_hint(self, locator: str) -> str:
        return self._loop._locator_label_hint(locator)

    def canonical_confirmed_execution_locator(self, locator: str) -> str:
        return self._loop._canonical_confirmed_execution_locator(locator)

    def match_tool_locator_call(self, locator: str, function_name: str) -> str:
        return self._loop._match_tool_locator_call(locator, function_name)

    def match_tool_locator_text(self, locator: str) -> Any:
        return self._loop._match_tool_locator_text(locator)

    def match_tool_locator_role(self, locator: str) -> Any:
        return self._loop._match_tool_locator_role(locator)

    def build_generated_line(self, action: str, locator: str, value: Any = None, **kwargs: Any) -> str:
        return self._loop._build_generated_line(action, locator, value, **kwargs)

    def locator_to_playwright_expression(self, locator: str) -> str:
        return self._loop._locator_to_playwright_expression(locator)

    def build_code_update_payload(self, payload: dict, step_id: str) -> dict:
        return self._loop._build_code_update_payload(payload, step_id)

    def derive_element_name(self, locator: str, element_info: Any = None) -> str:
        return self._loop._derive_element_name(locator, element_info)
