from __future__ import annotations

from copy import deepcopy

from runtime.context_manager import ContextManager
from runtime.history_manager import COMPACTION_SUMMARY_MESSAGE


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


def test_small_history_is_unchanged():
    manager = ContextManager()
    messages = _build_small_history()
    before = deepcopy(messages)

    bundle = manager.prepare_messages(
        messages,
        purpose="main_orchestrator",
        context_mode="normal",
        metadata={"skill_count": 1, "tool_count": 0},
    )

    assert bundle.messages == messages
    assert [message["role"] for message in bundle.messages] == [message["role"] for message in messages]
    assert messages == before
    assert bundle.metadata["managed_history_enabled"] is True
    assert bundle.metadata["compaction_applied"] is False
    assert bundle.metadata["original_message_count"] == len(messages)
    assert bundle.metadata["final_message_count"] == len(messages)
    assert bundle.metadata["original_estimated_tokens"] == bundle.metadata["final_estimated_tokens"]
    assert bundle.estimated_message_tokens == bundle.metadata["final_estimated_tokens"]
    assert bundle.message_count == len(messages)
    assert bundle.context_mode == "normal"


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
    assert bundle.metadata["compaction_applied"] is True
    assert bundle.metadata["original_message_count"] == len(messages)
    assert bundle.metadata["final_message_count"] == len(bundle.messages)
    assert bundle.metadata["final_message_count"] < bundle.metadata["original_message_count"]
    assert bundle.messages[0]["role"] == "system"
    assert bundle.messages[1]["role"] == "user"
    assert bundle.messages[1]["content"] == "original user intent: click the submit button"
    assert bundle.messages[2]["role"] == "system"
    assert bundle.messages[2]["content"] == COMPACTION_SUMMARY_MESSAGE
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
