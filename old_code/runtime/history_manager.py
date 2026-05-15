from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from runtime.telemetry import estimate_messages_tokens, estimate_text_tokens

PROTECTED_HISTORY_TOKEN_THRESHOLD = 6000
COMPACTION_SUMMARY_MESSAGE = (
    "ContextManager compacted older assistant/tool history. "
    "Preserved original intent, latest tool calls/results, and recent messages."
)


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


@dataclass(slots=True)
class ManagedHistoryResult:
    messages: list[dict[str, Any]]
    compaction_applied: bool
    original_message_count: int
    final_message_count: int
    original_estimated_tokens: int
    final_estimated_tokens: int
    preserved_reason_counts: dict[str, int]


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

    def build_managed_history(
        self,
        messages: list[dict[str, Any]] | None,
        *,
        metadata: dict[str, Any] | None = None,
        threshold: int = PROTECTED_HISTORY_TOKEN_THRESHOLD,
    ) -> ManagedHistoryResult:
        copied_messages = list(messages or [])
        original_message_count = len(copied_messages)
        original_estimated_tokens = estimate_messages_tokens(copied_messages)

        if original_estimated_tokens <= threshold:
            return ManagedHistoryResult(
                messages=copied_messages,
                compaction_applied=False,
                original_message_count=original_message_count,
                final_message_count=original_message_count,
                original_estimated_tokens=original_estimated_tokens,
                final_estimated_tokens=original_estimated_tokens,
                preserved_reason_counts={},
            )

        compacted_messages, preserved_reason_counts = self._compact_protected_history(
            copied_messages,
            metadata=metadata,
        )
        final_estimated_tokens = estimate_messages_tokens(compacted_messages)
        return ManagedHistoryResult(
            messages=compacted_messages,
            compaction_applied=True,
            original_message_count=original_message_count,
            final_message_count=len(compacted_messages),
            original_estimated_tokens=original_estimated_tokens,
            final_estimated_tokens=final_estimated_tokens,
            preserved_reason_counts=preserved_reason_counts,
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

    def _compact_protected_history(
        self,
        messages: list[dict[str, Any]],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        preserved_indices: set[int] = set()
        preserved_reason_counts: dict[str, int] = {}
        protected_tool_call_ids: set[str] = set()
        failure_recovery_enabled = self._metadata_indicates_failure_recovery(metadata)

        system_indices = [
            index for index, message in enumerate(messages) if self._message_role(message) == "system"
        ]
        for index in system_indices:
            self._mark_preserved_index(preserved_indices, preserved_reason_counts, index, "system_message")

        original_user_index = self._first_user_message_index(messages)
        if original_user_index is not None:
            self._mark_preserved_index(
                preserved_indices,
                preserved_reason_counts,
                original_user_index,
                "original_user_intent",
            )

        recent_non_system_indices = self._last_non_system_indices(messages, limit=6)
        for index in recent_non_system_indices:
            self._mark_preserved_index(
                preserved_indices,
                preserved_reason_counts,
                index,
                "recent_non_system",
            )
            protected_tool_call_ids.update(self._message_tool_call_ids(messages[index]))
            tool_call_id = self._message_tool_call_id(messages[index])
            if tool_call_id:
                protected_tool_call_ids.add(tool_call_id)

        latest_assistant_tool_call_index = self._latest_assistant_tool_call_index(messages)
        if latest_assistant_tool_call_index is not None:
            self._mark_preserved_index(
                preserved_indices,
                preserved_reason_counts,
                latest_assistant_tool_call_index,
                "latest_assistant_tool_calls",
            )
            protected_tool_call_ids.update(self._message_tool_call_ids(messages[latest_assistant_tool_call_index]))

        if failure_recovery_enabled:
            for index, message in enumerate(messages):
                if not self._message_is_failure_recovery_related(message):
                    continue
                self._mark_preserved_index(
                    preserved_indices,
                    preserved_reason_counts,
                    index,
                    "failure_recovery",
                )
                protected_tool_call_ids.update(self._message_tool_call_ids(message))
                tool_call_id = self._message_tool_call_id(message)
                if tool_call_id:
                    protected_tool_call_ids.add(tool_call_id)

        for index, message in enumerate(messages):
            role = self._message_role(message)
            if role == "assistant":
                tool_call_ids = set(self._message_tool_call_ids(message))
                if tool_call_ids.intersection(protected_tool_call_ids):
                    self._mark_preserved_index(
                        preserved_indices,
                        preserved_reason_counts,
                        index,
                        "tool_chain_assistant",
                    )
                    protected_tool_call_ids.update(tool_call_ids)
            elif role == "tool":
                tool_call_id = self._message_tool_call_id(message)
                if tool_call_id and tool_call_id in protected_tool_call_ids:
                    self._mark_preserved_index(
                        preserved_indices,
                        preserved_reason_counts,
                        index,
                        "recent_tool_call_result",
                    )

        summary_message = {
            "role": "system",
            "content": COMPACTION_SUMMARY_MESSAGE,
        }
        summary_insert_after_index = original_user_index
        if summary_insert_after_index is None:
            summary_insert_after_index = system_indices[0] if system_indices else None

        compacted_messages: list[dict[str, Any]] = []
        summary_inserted = False
        for index, message in enumerate(messages):
            if index in preserved_indices:
                compacted_messages.append(message)
            if (
                not summary_inserted
                and summary_insert_after_index is not None
                and index == summary_insert_after_index
            ):
                compacted_messages.append(summary_message)
                summary_inserted = True

        if summary_insert_after_index is None and not summary_inserted:
            compacted_messages.insert(0, summary_message)

        return compacted_messages, preserved_reason_counts

    def _mark_preserved_index(
        self,
        preserved_indices: set[int],
        preserved_reason_counts: dict[str, int],
        index: int,
        reason: str,
    ) -> None:
        if index < 0:
            return
        preserved_indices.add(index)
        preserved_reason_counts[reason] = preserved_reason_counts.get(reason, 0) + 1

    def _first_user_message_index(self, messages: list[dict[str, Any]]) -> int | None:
        for index, message in enumerate(messages):
            if self._message_role(message) == "user":
                return index
        return None

    def _last_non_system_indices(
        self,
        messages: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[int]:
        indices = [
            index
            for index, message in enumerate(messages)
            if self._message_role(message) != "system"
        ]
        if limit <= 0:
            return []
        return indices[-limit:]

    def _latest_assistant_tool_call_index(self, messages: list[dict[str, Any]]) -> int | None:
        for index in range(len(messages) - 1, -1, -1):
            message = messages[index]
            if self._message_role(message) != "assistant":
                continue
            if self._message_tool_call_ids(message):
                return index
        return None

    def _message_tool_call_ids(self, message: Any) -> list[str]:
        if not isinstance(message, dict):
            return []

        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            return []

        tool_call_ids: list[str] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_call_id = str(tool_call.get("id") or "").strip()
            if tool_call_id:
                tool_call_ids.append(tool_call_id)
        return tool_call_ids

    def _message_tool_call_id(self, message: Any) -> str:
        if not isinstance(message, dict):
            return ""
        return str(message.get("tool_call_id") or "").strip()

    def _metadata_indicates_failure_recovery(self, metadata: dict[str, Any] | None) -> bool:
        if not isinstance(metadata, dict):
            return False

        for key, value in metadata.items():
            if isinstance(key, str) and self._text_has_failure_recovery_marker(key):
                return True
            if isinstance(value, str) and self._text_has_failure_recovery_marker(value):
                return True
            if isinstance(value, dict) and self._metadata_indicates_failure_recovery(value):
                return True
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    if isinstance(item, str) and self._text_has_failure_recovery_marker(item):
                        return True
                    if isinstance(item, dict) and self._metadata_indicates_failure_recovery(item):
                        return True
        return False

    def _message_is_failure_recovery_related(self, message: Any) -> bool:
        if not isinstance(message, dict):
            return False

        for key, value in message.items():
            if isinstance(key, str) and self._text_has_failure_recovery_marker(key):
                return True
            if isinstance(value, str) and self._text_has_failure_recovery_marker(value):
                return True
            if isinstance(value, dict) and self._message_is_failure_recovery_related(value):
                return True
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    if isinstance(item, str) and self._text_has_failure_recovery_marker(item):
                        return True
                    if isinstance(item, dict) and self._message_is_failure_recovery_related(item):
                        return True
        return False

    def _text_has_failure_recovery_marker(self, value: str) -> bool:
        normalized_value = str(value or "").strip().lower()
        if not normalized_value:
            return False
        return any(
            marker in normalized_value
            for marker in (
                "failure",
                "failed",
                "recovery",
                "recover",
            )
        )

    def _suggested_future_mode(self, estimated_total_tokens: int) -> str:
        if estimated_total_tokens > 12000:
            return "needs_compaction_now"
        if estimated_total_tokens >= 6000:
            return "needs_compaction_soon"
        return "normal"
