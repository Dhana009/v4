from __future__ import annotations
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class LLMOrchestrator:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def should_request_user_followup(self, final_text: str, had_tool_failure: bool) -> bool:
        text = self._loop._normalize_space(final_text).lower()
        if not text:
            return had_tool_failure

        request_phrases = (
            "please advise",
            "how would you like to proceed",
            "await your instruction",
            "please confirm",
            "which option",
            "i need your input",
            "need your input",
            "i need your guidance",
            "can you clarify",
            "what should i do next",
            "please let me know how you would like to proceed",
            "please tell me how you would like to proceed",
            "what would you like me to do",
            "what would you like to do",
            "do you want me to",
            "would you like me to",
            "should i",
        )
        if any(phrase in text for phrase in request_phrases):
            return True

        blocked_phrases = (
            "cannot continue",
            "can't continue",
            "unable to continue",
            "unable to proceed",
            "i am blocked",
            "blocked",
            "stuck",
            "need guidance",
            "need correction",
            "need clarification",
            "need help",
            "i can't proceed",
            "i cannot proceed",
            "i am unable",
        )
        if any(phrase in text for phrase in blocked_phrases):
            return True

        if had_tool_failure and not self.looks_like_completion_message(text):
            return True

        return False

    def looks_like_completion_message(self, text: str) -> bool:
        normalized = self._loop._normalize_space(text).lower()
        if not normalized:
            return False

        word_patterns = (
            r"\bdone\b",
            r"\bfinished\b",
            r"\bcompleted\b",
            r"\bsuccessfully\b",
        )
        if any(re.search(pattern, normalized) for pattern in word_patterns):
            return True

        multi_word_phrases = (
            "task complete",
            "task is complete",
            "completed successfully",
            "all set",
            "wrapped up",
            "run is complete",
            "run complete",
        )
        return any(phrase in normalized for phrase in multi_word_phrases)

    def format_user_followup_message(self, answer: str, event_type: str) -> str:
        answer_text = self._loop._normalize_space(answer)
        if self.is_correction_followup(answer_text, event_type):
            details = answer_text or "the user requested a correction"
            return f"User correction: {details}. Revise the plan and continue safely."

        details = answer_text or "confirmed"
        return f"User confirmed: {details}. Continue safely from the current browser state."

    def is_correction_followup(self, answer: str, event_type: str) -> bool:
        if event_type == "correction":
            return True
        if event_type != "option_selected":
            return False

        normalized = self._loop._normalize_space(answer).lower()
        correction_markers = (
            "instead",
            "first",
            "then",
            "before",
            "after",
            "revise",
            "change",
            "fix",
            "retry",
            "go back",
            "navigate back",
            "assert",
            "click",
            "fill",
        )
        return any(marker in normalized for marker in correction_markers)

    def assistant_message_entry(self, message: Any) -> dict[str, Any]:
        entry: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in message.tool_calls
            ]
        return entry
