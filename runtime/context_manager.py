from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from runtime.history_manager import (
    PROTECTED_HISTORY_TOKEN_THRESHOLD,
    HistoryManager,
)
from runtime.page_intelligence import build_page_intelligence_packet
from runtime.telemetry import estimate_messages_tokens, estimate_text_tokens

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

# Sprint 3 INT-CTX-001: cap individual tool/DOM result messages at this token limit.
DOM_TOOL_RESULT_TOKEN_CAP = 800

PURPOSE_COMPACT_WINDOW_POLICIES = {
    "step_plan_normalizer": "planning_recent_tool_chain",
    "plan_diff_editor": "correction_only",
    "locator_specialist": "locator_recent_tool_chain",
    "recovery_diagnoser": "recovery_recent_evidence",
}
TOOL_CHAIN_RESTORATION_PURPOSES = {"step_plan_normalizer", "locator_specialist"}


def _message_role(message: Any) -> str:
    if not isinstance(message, dict):
        return "other"
    role = str(message.get("role") or "").strip().lower()
    if role in {"system", "user", "assistant", "tool"}:
        return role
    return "other"


def _message_tool_call_ids(message: Any) -> set[str]:
    if not isinstance(message, dict):
        return set()
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return set()
    result: set[str] = set()
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        tool_call_id = str(tool_call.get("id") or "").strip()
        if tool_call_id:
            result.add(tool_call_id)
    return result


def _message_tool_call_id(message: Any) -> str:
    if not isinstance(message, dict):
        return ""
    return str(message.get("tool_call_id") or "").strip()


def _message_text(message: Any) -> str:
    if not isinstance(message, dict):
        return str(message or "")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _first_user_message_index(messages: list[dict]) -> int | None:
    for index, message in enumerate(messages):
        if _message_role(message) == "user":
            return index
    return None


def _last_indices_for_roles(
    messages: list[dict],
    *,
    roles: set[str],
    limit: int,
    include_tool_calling_assistants: bool = True,
) -> list[int]:
    indices: list[int] = []
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        role = _message_role(message)
        if role not in roles:
            continue
        if (
            role == "assistant"
            and not include_tool_calling_assistants
            and _message_tool_call_ids(message)
        ):
            continue
        indices.append(index)
        if len(indices) >= limit:
            break
    return list(reversed(indices))


def _last_tool_chain_indices(messages: list[dict], *, chain_limit: int) -> list[int]:
    indices: set[int] = set()
    found_chains = 0
    seen_tool_call_ids: set[str] = set()
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if _message_role(message) != "tool":
            continue
        tool_call_id = _message_tool_call_id(message)
        if not tool_call_id or tool_call_id in seen_tool_call_ids:
            continue
        seen_tool_call_ids.add(tool_call_id)
        indices.add(index)
        for candidate_index in range(index - 1, -1, -1):
            candidate = messages[candidate_index]
            if _message_role(candidate) != "assistant":
                continue
            if tool_call_id in _message_tool_call_ids(candidate):
                indices.add(candidate_index)
                break
        found_chains += 1
        if found_chains >= chain_limit:
            break
    return sorted(indices)


def _message_is_failure_recovery_related(message: Any) -> bool:
    text = _message_text(message).lower()
    return any(marker in text for marker in ("failed", "failure", "recovery", "error", "retry", "blocked"))


def _find_source_message_indices(
    selected_messages: list[dict],
    source_messages: list[dict],
) -> tuple[list[int], dict[int, list[dict]]]:
    matched_indices: list[int] = []
    extras_after_source_index: dict[int, list[dict]] = {}
    source_cursor = 0
    last_matched_index = -1

    for message in selected_messages:
        matched_index: int | None = None
        for index in range(source_cursor, len(source_messages)):
            source_message = source_messages[index]
            if source_message is message or source_message == message:
                matched_index = index
                break
        if matched_index is None:
            extras_after_source_index.setdefault(last_matched_index, []).append(message)
            continue
        matched_indices.append(matched_index)
        source_cursor = matched_index + 1
        last_matched_index = matched_index

    return matched_indices, extras_after_source_index


def _expand_tool_call_chain_indices(
    source_messages: list[dict],
    selected_indices: list[int],
) -> set[int]:
    assistant_index_by_tool_call_id: dict[str, int] = {}
    assistant_tool_call_ids_by_index: dict[int, list[str]] = {}
    tool_indices_by_tool_call_id: dict[str, list[int]] = {}

    for index, message in enumerate(source_messages):
        role = _message_role(message)
        if role == "assistant":
            tool_call_ids = sorted(_message_tool_call_ids(message))
            if not tool_call_ids:
                continue
            assistant_tool_call_ids_by_index[index] = tool_call_ids
            for tool_call_id in tool_call_ids:
                assistant_index_by_tool_call_id[tool_call_id] = index
        elif role == "tool":
            tool_call_id = _message_tool_call_id(message)
            if not tool_call_id:
                continue
            tool_indices_by_tool_call_id.setdefault(tool_call_id, []).append(index)

    expanded_indices = set(selected_indices)
    changed = True
    while changed:
        changed = False
        for index in sorted(expanded_indices):
            message = source_messages[index]
            role = _message_role(message)
            if role == "assistant":
                for tool_call_id in assistant_tool_call_ids_by_index.get(index, []):
                    for tool_index in tool_indices_by_tool_call_id.get(tool_call_id, []):
                        if tool_index not in expanded_indices:
                            expanded_indices.add(tool_index)
                            changed = True
            elif role == "tool":
                tool_call_id = _message_tool_call_id(message)
                assistant_index = assistant_index_by_tool_call_id.get(tool_call_id)
                if assistant_index is None:
                    continue
                if assistant_index not in expanded_indices:
                    expanded_indices.add(assistant_index)
                    changed = True
                for sibling_tool_call_id in assistant_tool_call_ids_by_index.get(assistant_index, []):
                    for tool_index in tool_indices_by_tool_call_id.get(sibling_tool_call_id, []):
                        if tool_index not in expanded_indices:
                            expanded_indices.add(tool_index)
                            changed = True

    return expanded_indices


def _prune_orphaned_tool_call_messages(messages: list[dict]) -> list[dict]:
    tool_response_ids = {
        _message_tool_call_id(message)
        for message in messages
        if _message_role(message) == "tool" and _message_tool_call_id(message)
    }
    complete_assistant_tool_call_ids: set[str] = set()
    pruned_messages: list[dict] = []

    for message in messages:
        role = _message_role(message)
        if role != "assistant":
            continue
        tool_call_ids = _message_tool_call_ids(message)
        if not tool_call_ids:
            continue
        if tool_call_ids.issubset(tool_response_ids):
            complete_assistant_tool_call_ids.update(tool_call_ids)

    for message in messages:
        role = _message_role(message)
        if role == "assistant":
            tool_call_ids = _message_tool_call_ids(message)
            if tool_call_ids and not tool_call_ids.issubset(tool_response_ids):
                continue
            pruned_messages.append(message)
            continue
        if role == "tool":
            tool_call_id = _message_tool_call_id(message)
            if tool_call_id and tool_call_id not in complete_assistant_tool_call_ids:
                continue
            pruned_messages.append(message)
            continue
        pruned_messages.append(message)

    return pruned_messages


def _restore_complete_tool_call_chains(
    selected_messages: list[dict],
    *,
    source_messages: list[dict],
) -> list[dict]:
    matched_indices, extras_after_source_index = _find_source_message_indices(selected_messages, source_messages)
    expanded_indices = _expand_tool_call_chain_indices(source_messages, matched_indices)
    restored_messages: list[dict] = list(extras_after_source_index.get(-1, []))

    for index, message in enumerate(source_messages):
        if index in expanded_indices:
            restored_messages.append(message)
        restored_messages.extend(extras_after_source_index.get(index, []))

    return _prune_orphaned_tool_call_messages(restored_messages)


def _apply_purpose_compact_window(
    messages: list[dict],
    *,
    purpose: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[dict], dict[str, Any]]:
    normalized_purpose = str(purpose or "").strip()
    strategy = PURPOSE_COMPACT_WINDOW_POLICIES.get(normalized_purpose)
    if not strategy:
        return list(messages), {
            "applied": False,
            "strategy": "none",
            "dropped_count": 0,
        }

    selected_indices: set[int] = set()
    for index, message in enumerate(messages):
        if _message_role(message) == "system":
            selected_indices.add(index)

    first_user_index = _first_user_message_index(messages)
    if first_user_index is not None:
        selected_indices.add(first_user_index)

    if strategy == "planning_recent_tool_chain":
        selected_indices.update(
            _last_indices_for_roles(
                messages,
                roles={"user", "assistant"},
                limit=2,
                include_tool_calling_assistants=False,
            )
        )
        selected_indices.update(_last_tool_chain_indices(messages, chain_limit=1))
    elif strategy == "correction_only":
        selected_indices.update(
            _last_indices_for_roles(
                messages,
                roles={"user", "assistant"},
                limit=3,
                include_tool_calling_assistants=False,
            )
        )
    elif strategy == "locator_recent_tool_chain":
        selected_indices.update(_last_indices_for_roles(messages, roles={"user", "assistant"}, limit=2))
        selected_indices.update(_last_tool_chain_indices(messages, chain_limit=1))
    elif strategy == "recovery_recent_evidence":
        selected_indices.update(_last_indices_for_roles(messages, roles={"user", "assistant", "tool"}, limit=4))
        for index, message in enumerate(messages):
            if _message_is_failure_recovery_related(message):
                selected_indices.add(index)

    compacted_messages = [messages[index] for index in sorted(selected_indices)]
    dropped_count = max(0, len(messages) - len(compacted_messages))
    return compacted_messages, {
        "applied": dropped_count > 0,
        "strategy": strategy,
        "dropped_count": dropped_count,
    }


def _looks_like_html(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    return normalized.startswith("<") and any(tag in normalized for tag in ("<html", "<div", "<body", "<main", "<form", "<button"))


def _summarize_html_blob(text: str, *, url: str = "", title: str = "") -> str:
    packet = build_page_intelligence_packet(html=text, url=url, title=title)
    return packet.to_compact_summary()


def _summarize_structured_tool_payload(payload: Any) -> tuple[Any, bool]:
    changed = False
    if isinstance(payload, dict):
        summary = dict(payload)
        if "_raw_elements" in summary:
            summary.pop("_raw_elements", None)
            changed = True
        for key, value in list(summary.items()):
            if isinstance(value, str) and _looks_like_html(value):
                summary[key] = _summarize_html_blob(
                    value,
                    url=str(summary.get("url") or ""),
                    title=str(summary.get("title") or ""),
                )
                changed = True
            elif isinstance(value, list) and len(value) > 5:
                summary[key] = value[:5]
                changed = True
            elif isinstance(value, dict) and len(value) > 8:
                trimmed: dict[str, Any] = {}
                for index, (nested_key, nested_value) in enumerate(value.items()):
                    if index >= 8:
                        break
                    trimmed[nested_key] = nested_value
                summary[key] = trimmed
                changed = True
        elements_value = summary.get("elements")
        if isinstance(elements_value, str) and _looks_like_html(elements_value):
            summary["elements"] = _summarize_html_blob(
                elements_value,
                url=str(summary.get("url") or ""),
                title=str(summary.get("title") or ""),
            )
            changed = True
        return summary, changed
    if isinstance(payload, list) and len(payload) > 5:
        return payload[:5], True
    return payload, changed


def _summarize_tool_result_text(text: str) -> tuple[str, bool]:
    normalized = str(text or "")
    changed = False
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        parsed = None
    if parsed is not None:
        summarized_payload, payload_changed = _summarize_structured_tool_payload(parsed)
        if payload_changed:
            normalized = json.dumps(summarized_payload, ensure_ascii=True)
            changed = True
    elif _looks_like_html(normalized):
        normalized = _summarize_html_blob(normalized)
        changed = True
    return normalized, changed


def _cap_tool_result_messages(messages: list[dict]) -> tuple[list[dict], bool]:
    """Cap any tool-role message content exceeding DOM_TOOL_RESULT_TOKEN_CAP tokens.
    Returns (capped_messages, was_capped)."""
    capped = False
    result: list[dict] = []
    for message in messages:
        if not isinstance(message, dict) or str(message.get("role") or "") != "tool":
            result.append(message)
            continue
        content = message.get("content")
        if content is None:
            result.append(message)
            continue
        text = content if isinstance(content, str) else str(content)
        text, summarized = _summarize_tool_result_text(text)
        token_count = estimate_text_tokens(text)
        if token_count <= DOM_TOOL_RESULT_TOKEN_CAP:
            new_msg = dict(message)
            new_msg["content"] = text
            result.append(new_msg)
            capped = capped or summarized
            continue
        char_limit = DOM_TOOL_RESULT_TOKEN_CAP * 4
        truncated = text[:char_limit]
        new_msg = dict(message)
        new_msg["content"] = truncated + f"\n[TRUNCATED: {token_count} tokens capped to {DOM_TOOL_RESULT_TOKEN_CAP}]"
        result.append(new_msg)
        capped = True
    return result, capped


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
        original_messages = list(copied_messages)
        normalized_purpose = str(purpose or "").strip()
        copied_messages, purpose_window_details = _apply_purpose_compact_window(
            copied_messages,
            purpose=normalized_purpose,
            metadata=metadata,
        )
        if normalized_purpose in TOOL_CHAIN_RESTORATION_PURPOSES:
            copied_messages = _restore_complete_tool_call_chains(
                copied_messages,
                source_messages=original_messages,
            )
        # INT-CTX-001: cap tool/DOM result messages before history analysis
        copied_messages, tool_result_capped = _cap_tool_result_messages(copied_messages)
        history_source_messages = list(copied_messages)
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
        if normalized_purpose in TOOL_CHAIN_RESTORATION_PURPOSES:
            final_messages = _restore_complete_tool_call_chains(
                final_messages,
                source_messages=history_source_messages,
            )
        recovery_scope_instruction_applied = False
        execution_context = str(bundle_metadata.get("execution_context") or "").strip()
        correction_context = str(bundle_metadata.get("correction_context") or "").strip()
        phase_insert_index = 0
        for index, message in enumerate(final_messages):
            if isinstance(message, dict) and str(message.get("role") or "").strip().lower() == "system":
                phase_insert_index = index + 1
                break
        if phase_instruction is not None:
            final_messages.insert(phase_insert_index, phase_instruction)
            insertion_index = phase_insert_index + 1
            if execution_context:
                final_messages.insert(insertion_index, {"role": "system", "content": execution_context})
                insertion_index += 1
            if correction_context:
                final_messages.insert(insertion_index, {"role": "system", "content": correction_context})
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
        # INT-CTX-001: derive budget_status
        if managed_history.compaction_applied and tool_result_capped:
            budget_status = "compacted"
        elif managed_history.compaction_applied:
            budget_status = "compacted"
        elif tool_result_capped:
            budget_status = "capped"
        else:
            budget_status = "ok"

        bundle_metadata["budget_status"] = budget_status
        bundle_metadata["tool_result_capped"] = tool_result_capped
        bundle_metadata["purpose_window_applied"] = bool(purpose_window_details.get("applied"))
        bundle_metadata["purpose_window_strategy"] = str(purpose_window_details.get("strategy") or "none")
        bundle_metadata["purpose_window_dropped_count"] = int(purpose_window_details.get("dropped_count") or 0)
        bundle_metadata["managed_history_enabled"] = True
        bundle_metadata["compaction_applied"] = managed_history.compaction_applied
        bundle_metadata["original_message_count"] = managed_history.original_message_count
        bundle_metadata["final_message_count"] = final_message_count
        bundle_metadata["original_estimated_tokens"] = managed_history.original_estimated_tokens
        bundle_metadata["final_estimated_tokens"] = estimated_message_tokens
        bundle_metadata["preserved_reason_counts"] = dict(managed_history.preserved_reason_counts)
        bundle_metadata["purpose"] = normalized_purpose or "unknown"
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
            f"budget_status={budget_status} "
            f"compacted={'true' if managed_history.compaction_applied else 'false'} "
            f"tool_result_capped={'true' if tool_result_capped else 'false'} "
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
