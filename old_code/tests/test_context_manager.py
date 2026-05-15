from __future__ import annotations

from copy import deepcopy

from runtime.context_manager import ContextManager
from runtime.history_manager import COMPACTION_SUMMARY_MESSAGE

PLANNING_PHASE_INSTRUCTION = (
    "Phase: planning. You may inspect page state, extract DOM, find and validate "
    "locators, ask clarification, and send plan_ready. Do not call execution tools. "
    "Do not claim the step is completed."
)
EXECUTING_PHASE_INSTRUCTION = (
    "Phase: executing. Execute only the confirmed plan. Do not change user intent. "
    "If execution succeeds, proceed toward recording. If execution fails, report "
    "failure or recovery."
)
RECOVERY_PHASE_INSTRUCTION = (
    "Phase: recovery. Stay anchored to the failed step or operation. Suggest or "
    "perform only recovery actions allowed by runtime."
)


def _build_small_history() -> list[dict[str, object]]:
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "click the submit button"},
        {"role": "assistant", "content": "acknowledged"},
    ]


def _build_large_history() -> list[dict[str, object]]:
    long_tail = "x" * 3000
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "original user intent: click the submit button"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "dom_extract",
                        "arguments": '{"scope":"page"}',
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-1", "content": '{"elements":["submit"]}'},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-2",
                    "type": "function",
                    "function": {
                        "name": "action_click",
                        "arguments": '{"locator":"button"}',
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-2", "content": '{"success":true}'},
        {"role": "user", "content": f"filler-0 {long_tail}"},
        {"role": "assistant", "content": f"filler-1 {long_tail}"},
        {"role": "user", "content": f"filler-2 {long_tail}"},
        {"role": "assistant", "content": f"filler-3 {long_tail}"},
        {"role": "user", "content": f"filler-4 {long_tail}"},
        {"role": "assistant", "content": f"filler-5 {long_tail}"},
        {"role": "user", "content": f"filler-6 {long_tail}"},
        {"role": "assistant", "content": f"filler-7 {long_tail}"},
    ]


def _non_system_messages(messages: list[dict[str, object]]) -> list[dict[str, object]]:
    return [message for message in messages if message.get("role") != "system"]


def test_planning_phase_inserts_planning_instruction():
    manager = ContextManager()
    messages = _build_small_history()
    before = deepcopy(messages)

    bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"skill_count": 1, "tool_count": 0, "phase": "planning"},
    )

    assert bundle.messages[1]["role"] == "system"
    assert bundle.messages[1]["content"] == PLANNING_PHASE_INSTRUCTION
    assert bundle.messages[2]["role"] == "user"
    assert bundle.messages[2]["content"] == "click the submit button"
    assert [message["role"] for message in bundle.messages] == ["system", "system", "user", "assistant"]
    assert messages == before
    assert bundle.metadata["managed_history_enabled"] is True
    assert bundle.metadata["phase"] == "planning"
    assert bundle.metadata["phase_instruction_applied"] is True
    assert bundle.metadata["compaction_applied"] is False
    assert bundle.metadata["original_message_count"] == len(messages)
    assert bundle.metadata["final_message_count"] == len(messages) + 1
    assert bundle.estimated_message_tokens == bundle.metadata["final_estimated_tokens"]
    assert bundle.message_count == len(messages) + 1
    assert bundle.context_mode == "normal"


def test_planning_phase_inserts_correction_context_after_phase_instruction():
    manager = ContextManager()
    messages = _build_small_history()
    correction_context = "Structured correction diff context.\nactive_plan_id: \"plan-1\""
    before = deepcopy(messages)

    bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={
            "skill_count": 1,
            "tool_count": 0,
            "phase": "planning",
            "correction_context": correction_context,
        },
    )

    assert bundle.messages[1]["role"] == "system"
    assert bundle.messages[1]["content"] == PLANNING_PHASE_INSTRUCTION
    assert bundle.messages[2]["role"] == "system"
    assert bundle.messages[2]["content"] == correction_context
    assert bundle.messages[3]["role"] == "user"
    assert bundle.messages[4]["role"] == "assistant"
    assert messages == before
    assert bundle.metadata["phase"] == "planning"
    assert bundle.metadata["phase_instruction_applied"] is True
    assert bundle.metadata["final_message_count"] == len(messages) + 2


def test_executing_phase_inserts_executing_instruction():
    manager = ContextManager()
    messages = _build_small_history()
    before = deepcopy(messages)

    bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"skill_count": 1, "tool_count": 0, "phase": "executing"},
    )

    assert bundle.messages[1]["role"] == "system"
    assert bundle.messages[1]["content"] == EXECUTING_PHASE_INSTRUCTION
    assert messages == before
    assert bundle.metadata["phase"] == "executing"
    assert bundle.metadata["phase_instruction_applied"] is True
    assert bundle.metadata["final_message_count"] == len(messages) + 1
    assert bundle.message_count == len(messages) + 1


def test_missing_or_unknown_phase_uses_planning_safe_instruction():
    manager = ContextManager()
    messages = _build_small_history()

    missing_bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"skill_count": 1, "tool_count": 0},
    )
    unknown_bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"skill_count": 1, "tool_count": 0, "phase": "mystery"},
    )

    assert missing_bundle.messages[1]["content"] == PLANNING_PHASE_INSTRUCTION
    assert missing_bundle.metadata["phase"] == "planning"
    assert missing_bundle.metadata["phase_instruction_applied"] is True
    assert unknown_bundle.messages[1]["content"] == PLANNING_PHASE_INSTRUCTION
    assert unknown_bundle.metadata["phase"] == "planning"
    assert unknown_bundle.metadata["phase_instruction_applied"] is True


def test_large_history_compacts_with_protected_preservation():
    manager = ContextManager()
    messages = _build_large_history()

    bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"phase": "recovery", "skill_count": 1, "tool_count": 1},
    )

    assert bundle.metadata["managed_history_enabled"] is True
    assert bundle.metadata["phase"] == "recovery"
    assert bundle.metadata["phase_instruction_applied"] is True
    assert bundle.metadata["compaction_applied"] is True
    assert bundle.metadata["original_message_count"] == len(messages)
    assert bundle.metadata["final_message_count"] == len(bundle.messages)
    assert bundle.metadata["final_message_count"] < bundle.metadata["original_message_count"]
    assert bundle.messages[0]["role"] == "system"
    assert bundle.messages[1]["role"] == "system"
    assert bundle.messages[1]["content"] == RECOVERY_PHASE_INSTRUCTION
    assert bundle.messages[2]["role"] == "user"
    assert bundle.messages[2]["content"] == "original user intent: click the submit button"
    assert bundle.messages[3]["role"] == "system"
    assert bundle.messages[3]["content"] == COMPACTION_SUMMARY_MESSAGE
    assert any(
        message.get("role") == "assistant"
        and message.get("tool_calls")
        and message["tool_calls"][0]["id"] == "call-2"
        for message in bundle.messages
    )
    assert any(
        message.get("role") == "tool" and message.get("tool_call_id") == "call-2"
        for message in bundle.messages
    )

    original_tail = _non_system_messages(messages)[-6:]
    final_tail = _non_system_messages(bundle.messages)[-6:]
    assert final_tail == original_tail
    assert bundle.metadata["context_mode"] == "protected"
    assert bundle.context_mode == "protected"
    assert bundle.message_count == bundle.metadata["final_message_count"]
    assert bundle.estimated_message_tokens == bundle.metadata["final_estimated_tokens"]


def test_original_messages_are_not_mutated():
    manager = ContextManager()
    messages = _build_large_history()
    before = deepcopy(messages)

    manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"phase": "recovery", "skill_count": 1, "tool_count": 1},
    )

    assert messages == before


def test_correction_context_is_injected_into_system_messages():
    manager = ContextManager()
    messages = _build_small_history()
    correction_context = (
        "Structured correction diff context.\n"
        "active_plan_id: \"plan-1\"\n"
        "target_step_id: \"step-1\"\n"
        "correction_type: \"add_and_reorder_operations\"\n"
        "Correction: \"assert first then click\"\n"
        "You MUST respond with send_to_overlay message_type='plan_correction_diff'.\n"
        "Do NOT respond with plan_ready during correction mode.\n"
    )

    bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"phase": "planning", "skill_count": 1, "tool_count": 1, "correction_context": correction_context},
    )

    correction_system_messages = [
        msg for msg in bundle.messages
        if msg.get("role") == "system"
        and "plan_correction_diff" in str(msg.get("content") or "")
    ]
    assert len(correction_system_messages) >= 1
    assert "You MUST respond with send_to_overlay" in str(correction_system_messages[0]["content"])
    assert "Do NOT respond with plan_ready" in str(correction_system_messages[0]["content"])


def test_correction_context_not_injected_when_empty():
    manager = ContextManager()
    messages = _build_small_history()

    bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"phase": "planning", "skill_count": 1, "tool_count": 1, "correction_context": ""},
    )

    correction_system_messages = [
        msg for msg in bundle.messages
        if msg.get("role") == "system"
        and "plan_correction_diff" in str(msg.get("content") or "")
    ]
    assert len(correction_system_messages) == 0


def test_context_does_not_ask_for_plan_ready_in_correction_mode():
    manager = ContextManager()
    messages = _build_small_history()
    correction_context = (
        "Structured correction diff context.\n"
        "active_plan_id: \"plan-1\"\n"
        "target_step_id: \"step-1\"\n"
        "correction_type: \"add_operation\"\n"
        "Correction: \"add assertion\"\n"
        "You MUST respond with send_to_overlay message_type='plan_correction_diff'.\n"
    )

    bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"phase": "planning", "skill_count": 1, "tool_count": 1, "correction_context": correction_context},
    )

    phase_messages = [msg for msg in bundle.messages if msg.get("role") == "system"]
    correction_messages = [msg for msg in phase_messages if "Structured correction diff context" in str(msg.get("content") or "")]
    assert len(correction_messages) >= 1
    correction_text = str(correction_messages[0]["content"])
    assert "message_type='plan_correction_diff'" in correction_text


def test_step_plan_normalizer_excludes_old_tool_outputs():
    manager = ContextManager()
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "click the selected button"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-old",
                    "type": "function",
                    "function": {"name": "dom_extract", "arguments": '{"scope":"page"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-old", "content": '{"elements":"old dom packet"}'},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-new",
                    "type": "function",
                    "function": {"name": "browser_get_state", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-new", "content": '{"url":"http://fixture/current"}'},
        {"role": "assistant", "content": "I have the latest page summary."},
    ]

    bundle = manager.prepare_messages(
        messages,
        purpose="step_plan_normalizer",
        context_mode="normal",
        metadata={"phase": "planning", "skill_count": 1, "tool_count": 2},
    )

    tool_call_ids = [msg.get("tool_call_id") for msg in bundle.messages if msg.get("role") == "tool"]
    assert "call-old" not in tool_call_ids
    assert "call-new" in tool_call_ids
    assert bundle.metadata["purpose_window_applied"] is True
    assert bundle.metadata["purpose_window_strategy"] == "planning_recent_tool_chain"


def test_plan_diff_editor_excludes_dom_history_and_tools():
    manager = ContextManager()
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "click the selected button"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-dom",
                    "type": "function",
                    "function": {"name": "dom_extract", "arguments": '{"scope":"page"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-dom", "content": '{"elements":"dom snapshot"}'},
        {"role": "assistant", "content": "Here is the plan."},
        {"role": "user", "content": "Correction: add an assertion first."},
    ]

    bundle = manager.prepare_messages(
        messages,
        purpose="plan_diff_editor",
        context_mode="normal",
        metadata={
            "phase": "planning",
            "skill_count": 1,
            "tool_count": 0,
            "correction_context": "Structured correction diff context.",
        },
    )

    assert not any(msg.get("role") == "tool" for msg in bundle.messages)
    assert not any(msg.get("tool_calls") for msg in bundle.messages if msg.get("role") == "assistant")
    assert any("Correction: add an assertion first." in str(msg.get("content") or "") for msg in bundle.messages)
    assert bundle.metadata["purpose_window_strategy"] == "correction_only"


def test_locator_specialist_keeps_only_recent_locator_chain():
    manager = ContextManager()
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "find the locator"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-older",
                    "type": "function",
                    "function": {"name": "locator_find", "arguments": '{"target":"old"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-older", "content": '{"locator":"old-locator"}'},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-recent",
                    "type": "function",
                    "function": {"name": "locator_validate", "arguments": '{"locator":"new-locator"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-recent", "content": '{"valid":true,"locator":"new-locator"}'},
        {"role": "assistant", "content": "Latest locator candidate is new-locator."},
    ]

    bundle = manager.prepare_messages(
        messages,
        purpose="locator_specialist",
        context_mode="normal",
        metadata={"phase": "planning", "skill_count": 1, "tool_count": 2},
    )

    serialized = "\n".join(str(msg.get("content") or "") for msg in bundle.messages if isinstance(msg, dict))
    assert "new-locator" in serialized
    assert "old-locator" not in serialized
    assert bundle.metadata["purpose_window_strategy"] == "locator_recent_tool_chain"


def test_recovery_diagnoser_keeps_failure_context_and_recent_evidence():
    manager = ContextManager()
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "click the submit button"},
        {"role": "assistant", "content": "The click failed with timeout."},
        {"role": "tool", "tool_call_id": "call-failure", "content": '{"success":false,"error":"timeout while clicking"}'},
        {"role": "assistant", "content": "Recovery: retry after checking visibility."},
        {"role": "user", "content": "please continue recovery"},
        {"role": "assistant", "content": "Latest evidence collected."},
    ]

    bundle = manager.prepare_messages(
        messages,
        purpose="recovery_diagnoser",
        context_mode="normal",
        metadata={"phase": "recovery", "skill_count": 1, "tool_count": 1},
    )

    serialized = "\n".join(str(msg.get("content") or "") for msg in bundle.messages if isinstance(msg, dict))
    assert "timeout while clicking" in serialized
    assert "continue recovery" in serialized
    assert bundle.metadata["purpose_window_strategy"] == "recovery_recent_evidence"


def test_step_plan_normalizer_does_not_keep_orphaned_tool_call_messages():
    manager = ContextManager()
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "assert this is visible"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-old",
                    "type": "function",
                    "function": {"name": "send_to_overlay", "arguments": '{"message_type":"llm_thinking"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-old", "content": '{"sent":true}'},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-new",
                    "type": "function",
                    "function": {"name": "send_to_overlay", "arguments": '{"message_type":"llm_thinking"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-new", "content": '{"sent":true}'},
    ]

    bundle = manager.prepare_messages(
        messages,
        purpose="step_plan_normalizer",
        context_mode="normal",
        metadata={"phase": "planning", "skill_count": 1, "tool_count": 1},
    )

    assistant_tool_call_ids = {
        tool_call["id"]
        for message in bundle.messages
        if message.get("role") == "assistant"
        for tool_call in (message.get("tool_calls") or [])
        if isinstance(tool_call, dict) and str(tool_call.get("id") or "").strip()
    }
    tool_response_ids = {
        str(message.get("tool_call_id") or "").strip()
        for message in bundle.messages
        if message.get("role") == "tool"
    }

    assert assistant_tool_call_ids == tool_response_ids


def test_step_plan_normalizer_keeps_complete_multi_tool_call_chain():
    manager = ContextManager()
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "inspect the selected element"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-first",
                    "type": "function",
                    "function": {"name": "browser_get_state", "arguments": "{}"},
                },
                {
                    "id": "call-second",
                    "type": "function",
                    "function": {"name": "dom_extract", "arguments": '{"scope":"page"}'},
                },
            ],
        },
        {"role": "tool", "tool_call_id": "call-first", "content": '{"url":"http://fixture/current"}'},
        {"role": "tool", "tool_call_id": "call-second", "content": '{"elements":["Get started"]}'},
        {"role": "assistant", "content": "I have the latest page summary."},
    ]

    bundle = manager.prepare_messages(
        messages,
        purpose="step_plan_normalizer",
        context_mode="normal",
        metadata={"phase": "planning", "skill_count": 1, "tool_count": 2},
    )

    assistant_tool_call_ids = [
        sorted(
            str(tool_call.get("id") or "").strip()
            for tool_call in (message.get("tool_calls") or [])
            if isinstance(tool_call, dict)
        )
        for message in bundle.messages
        if message.get("role") == "assistant" and message.get("tool_calls")
    ]
    tool_response_ids = sorted(
        str(message.get("tool_call_id") or "").strip()
        for message in bundle.messages
        if message.get("role") == "tool"
    )

    assert ["call-first", "call-second"] in assistant_tool_call_ids
    assert tool_response_ids == ["call-first", "call-second"]
