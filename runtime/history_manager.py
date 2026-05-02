from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from runtime.telemetry import estimate_messages_tokens, estimate_text_tokens


@dataclass(slots=True)
class HistoryDiagnostics:
    total_messages: int
    system_messages: int
    user_messages: int
    assistant_messages: int
    tool_messages: int
    other_messages: int
    estimated_total_tokens: int
    estimated_system_tokens: int
    estimated_user_tokens: int
    estimated_assistant_tokens: int
    estimated_tool_tokens: int
    largest_message_role: str
    largest_message_estimated_tokens: int
    last_message_role: str
    tool_result_count: int
    assistant_tool_call_count: int
    suggested_future_mode: str

    def to_summary_dict(self) -> dict[str, Any]:
        return asdict(self)


class HistoryManager:
    def analyze(self, messages: list[dict[str, Any]] | None) -> HistoryDiagnostics:
        copied_messages = list(messages or [])

        total_messages = len(copied_messages)
        system_messages = 0
        user_messages = 0
        assistant_messages = 0
        tool_messages = 0
        other_messages = 0
        estimated_system_tokens = 0
        estimated_user_tokens = 0
        estimated_assistant_tokens = 0
        estimated_tool_tokens = 0
        largest_message_role = "none"
        largest_message_estimated_tokens = 0
        last_message_role = "none"
        tool_result_count = 0
        assistant_tool_call_count = 0

        for message in copied_messages:
            role = self._message_role(message)
            message_tokens = self._estimate_message_tokens(message)

            if role == "system":
                system_messages += 1
                estimated_system_tokens += message_tokens
            elif role == "user":
                user_messages += 1
                estimated_user_tokens += message_tokens
            elif role == "assistant":
                assistant_messages += 1
                estimated_assistant_tokens += message_tokens
                assistant_tool_call_count += self._assistant_tool_call_count(message)
            elif role == "tool":
                tool_messages += 1
                tool_result_count += 1
                estimated_tool_tokens += message_tokens
            else:
                other_messages += 1

            if message_tokens > largest_message_estimated_tokens:
                largest_message_role = role
                largest_message_estimated_tokens = message_tokens

            last_message_role = role

        estimated_total_tokens = estimate_messages_tokens(copied_messages)
        suggested_future_mode = self._suggested_future_mode(estimated_total_tokens)

        return HistoryDiagnostics(
            total_messages=total_messages,
            system_messages=system_messages,
            user_messages=user_messages,
            assistant_messages=assistant_messages,
            tool_messages=tool_messages,
            other_messages=other_messages,
            estimated_total_tokens=estimated_total_tokens,
            estimated_system_tokens=estimated_system_tokens,
            estimated_user_tokens=estimated_user_tokens,
            estimated_assistant_tokens=estimated_assistant_tokens,
            estimated_tool_tokens=estimated_tool_tokens,
            largest_message_role=largest_message_role,
            largest_message_estimated_tokens=largest_message_estimated_tokens,
            last_message_role=last_message_role,
            tool_result_count=tool_result_count,
            assistant_tool_call_count=assistant_tool_call_count,
            suggested_future_mode=suggested_future_mode,
        )

    def _message_role(self, message: Any) -> str:
        if not isinstance(message, dict):
            return "other"

        role = str(message.get("role") or "").strip().lower()
        if role in {"system", "user", "assistant", "tool"}:
            return role
        return "other"

    def _estimate_message_tokens(self, message: Any) -> int:
        try:
            return estimate_messages_tokens([message])
        except Exception:  # noqa: BLE001
            return estimate_text_tokens(str(message)) + 4

    def _assistant_tool_call_count(self, message: Any) -> int:
        if not isinstance(message, dict):
            return 0

        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            return len(tool_calls)
        return 0

    def _suggested_future_mode(self, estimated_total_tokens: int) -> str:
        if estimated_total_tokens > 12000:
            return "needs_compaction_now"
        if estimated_total_tokens >= 6000:
            return "needs_compaction_soon"
        return "normal"
