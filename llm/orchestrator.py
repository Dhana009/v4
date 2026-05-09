from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class LLMOrchestrator:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def should_request_user_followup(self, final_text: str, had_tool_failure: bool) -> bool:
        return self._loop._should_request_user_followup(final_text, had_tool_failure)

    def looks_like_completion_message(self, text: str) -> bool:
        return self._loop._looks_like_completion_message(text)

    def format_user_followup_message(self, answer: str, event_type: str) -> str:
        return self._loop._format_user_followup_message(answer, event_type)

    def is_correction_followup(self, answer: str, event_type: str) -> bool:
        return self._loop._is_correction_followup(answer, event_type)

    def assistant_message_entry(self, message: Any) -> dict[str, Any]:
        return self._loop._assistant_message_entry(message)
