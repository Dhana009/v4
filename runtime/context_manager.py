from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.history_manager import (
    PROTECTED_HISTORY_TOKEN_THRESHOLD,
    HistoryManager,
)
from runtime.telemetry import estimate_messages_tokens

PHASE_INSTRUCTION_CONTENT = {
    "planning": (
        "Phase: planning. You may inspect page state, extract DOM, find and validate "
        "locators, ask clarification, and send plan_ready. Do not call execution tools. "
        "Do not claim the step is completed."
    ),
    "awaiting_confirmation": (
        "Phase: awaiting_confirmation. Wait for user confirmation or correction. Do "
        "not execute actions. Do not record steps."
    ),
    "executing": (
        "Phase: executing. Execute only the confirmed plan. Do not change user intent. "
        "If execution succeeds, proceed toward recording. If execution fails, report "
        "failure or recovery."
    ),
    "recording": (
        "Phase: recording. Record only actions or assertions that already succeeded. Do "
        "not perform new browser actions unless explicitly required by runtime."
    ),
    "recovery": (
        "Phase: recovery. Stay anchored to the failed step or operation. Suggest or "
        "perform only recovery actions allowed by runtime."
    ),
}

RECOVERY_SCOPE_INSTRUCTION = (
    "Completed/recorded steps are locked. Do not replan completed steps. Do not send "
    "plan_ready during unresolved recovery. Work only on the failed unresolved step. "
    "Allowed outcomes: retry or repair the failed step, ask user, skip, stop/end."
)


def _build_phase_instruction(context_mode: str, phase: str | None) -> dict | None:
    normalized_phase = str(phase or "").strip().lower()
    if normalized_phase not in PHASE_INSTRUCTION_CONTENT:
        normalized_phase = "planning"
    return {"role": "system", "content": PHASE_INSTRUCTION_CONTENT[normalized_phase]}


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
        bundle_metadata: dict[str, Any] = dict(metadata or {})
        requested_phase = str(bundle_metadata.get("phase") or "").strip().lower()
        if requested_phase not in PHASE_INSTRUCTION_CONTENT:
            requested_phase = "planning"
        phase_instruction = _build_phase_instruction(context_mode, requested_phase)
        final_messages = list(managed_history.messages)
        recovery_scope_instruction_applied = False
        correction_context = str(bundle_metadata.get("correction_context") or "").strip()
        phase_insert_index = 0
        for index, message in enumerate(final_messages):
            if isinstance(message, dict) and str(message.get("role") or "").strip().lower() == "system":
                phase_insert_index = index + 1
                break
        if phase_instruction is not None:
            final_messages.insert(phase_insert_index, phase_instruction)
            if correction_context:
                final_messages.insert(phase_insert_index + 1, {"role": "system", "content": correction_context})
            if requested_phase == "recovery":
                if phase_insert_index > 0:
                    first_system_message = final_messages[0] if final_messages else None
                    if isinstance(first_system_message, dict):
                        existing_content = str(first_system_message.get("content") or "")
                        first_system_message["content"] = (
                            f"{existing_content}\n\n{RECOVERY_SCOPE_INSTRUCTION}".strip()
                            if existing_content
                            else RECOVERY_SCOPE_INSTRUCTION
                        )
                        recovery_scope_instruction_applied = True
                if not recovery_scope_instruction_applied and isinstance(phase_instruction, dict):
                    existing_content = str(phase_instruction.get("content") or "")
                    phase_instruction["content"] = (
                        f"{existing_content}\n\n{RECOVERY_SCOPE_INSTRUCTION}".strip()
                        if existing_content
                        else RECOVERY_SCOPE_INSTRUCTION
                    )
        final_message_count = len(final_messages)
        estimated_message_tokens = estimate_messages_tokens(final_messages)
        bundle_metadata["managed_history_enabled"] = True
        bundle_metadata["compaction_applied"] = managed_history.compaction_applied
        bundle_metadata["original_message_count"] = managed_history.original_message_count
        bundle_metadata["final_message_count"] = final_message_count
        bundle_metadata["original_estimated_tokens"] = managed_history.original_estimated_tokens
        bundle_metadata["final_estimated_tokens"] = estimated_message_tokens
        bundle_metadata["preserved_reason_counts"] = dict(managed_history.preserved_reason_counts)
        bundle_metadata["purpose"] = str(purpose or "").strip() or "unknown"
        bundle_metadata["phase"] = requested_phase
        bundle_metadata["phase_instruction_applied"] = phase_instruction is not None
        bundle_metadata["recovery_scope_instruction_applied"] = recovery_scope_instruction_applied
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
            f"final_messages={final_message_count} "
            f"original_tokens={managed_history.original_estimated_tokens} "
            f"final_tokens={estimated_message_tokens}"
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
            messages=final_messages,
            purpose=bundle_metadata["purpose"],
            context_mode=bundle_metadata["context_mode"],
            message_count=final_message_count,
            estimated_message_tokens=estimated_message_tokens,
            metadata=bundle_metadata,
        )
