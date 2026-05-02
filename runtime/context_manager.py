from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.history_manager import (
    PROTECTED_HISTORY_TOKEN_THRESHOLD,
    HistoryManager,
)


@dataclass(slots=True)
class ContextBundle:
    messages: list[dict]
    purpose: str
    context_mode: str
    message_count: int
    estimated_message_tokens: int
    metadata: dict[str, Any]


class ContextManager:
    def prepare_messages(
        self,
        messages: list[dict],
        *,
        purpose: str,
        run_id: str | None = None,
        step_id: str | None = None,
        context_mode: str = "normal",
        metadata: dict | None = None,
    ) -> ContextBundle:
        copied_messages = [
            dict(message) if isinstance(message, dict) else message
            for message in (messages or [])
        ]
        history_manager = HistoryManager()
        history_diagnostics = history_manager.analyze(copied_messages)
        managed_history = history_manager.build_managed_history(
            copied_messages,
            metadata=metadata,
            threshold=PROTECTED_HISTORY_TOKEN_THRESHOLD,
        )
        message_count = managed_history.final_message_count
        estimated_message_tokens = managed_history.final_estimated_tokens
        bundle_metadata: dict[str, Any] = dict(metadata or {})
        bundle_metadata["managed_history_enabled"] = True
        bundle_metadata["compaction_applied"] = managed_history.compaction_applied
        bundle_metadata["original_message_count"] = managed_history.original_message_count
        bundle_metadata["final_message_count"] = managed_history.final_message_count
        bundle_metadata["original_estimated_tokens"] = managed_history.original_estimated_tokens
        bundle_metadata["final_estimated_tokens"] = managed_history.final_estimated_tokens
        bundle_metadata["preserved_reason_counts"] = dict(managed_history.preserved_reason_counts)
        bundle_metadata["purpose"] = str(purpose or "").strip() or "unknown"
        requested_context_mode = str(context_mode or "").strip() or "normal"
        bundle_metadata["context_mode"] = (
            "protected" if managed_history.compaction_applied else requested_context_mode
        )
        bundle_metadata["history_diagnostics"] = history_diagnostics.to_summary_dict()
        if run_id is not None:
            bundle_metadata["run_id"] = run_id
        if step_id is not None:
            bundle_metadata["step_id"] = step_id

        print(
            "[CONTEXT_MANAGER] "
            f"purpose={bundle_metadata['purpose']} "
            f"mode={bundle_metadata['context_mode']} "
            f"compacted={'true' if managed_history.compaction_applied else 'false'} "
            f"original_messages={managed_history.original_message_count} "
            f"final_messages={managed_history.final_message_count} "
            f"original_tokens={managed_history.original_estimated_tokens} "
            f"final_tokens={managed_history.final_estimated_tokens}"
        )
        print(
            "[HISTORY_DIAGNOSTICS] "
            f"messages={history_diagnostics.total_messages} "
            f"system={history_diagnostics.system_messages} "
            f"user={history_diagnostics.user_messages} "
            f"assistant={history_diagnostics.assistant_messages} "
            f"tool={history_diagnostics.tool_messages} "
            f"estimated_tokens={history_diagnostics.estimated_total_tokens} "
            f"tool_tokens={history_diagnostics.estimated_tool_tokens} "
            f"largest_role={history_diagnostics.largest_message_role} "
            f"largest_tokens={history_diagnostics.largest_message_estimated_tokens} "
            f"mode={history_diagnostics.suggested_future_mode}"
        )

        return ContextBundle(
            messages=managed_history.messages,
            purpose=bundle_metadata["purpose"],
            context_mode=bundle_metadata["context_mode"],
            message_count=message_count,
            estimated_message_tokens=estimated_message_tokens,
            metadata=bundle_metadata,
        )
