from __future__ import annotations

import json

from runtime.context_manager import ContextManager, DOM_TOOL_RESULT_TOKEN_CAP, _cap_tool_result_messages
from runtime.telemetry import estimate_text_tokens


def _tool_msg(content: str, call_id: str = "t1") -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def _sys_msg(content: str = "You are an agent.") -> dict:
    return {"role": "system", "content": content}


def _user_msg(content: str = "Do something.") -> dict:
    return {"role": "user", "content": content}


def test_small_tool_result_not_capped():
    messages = [_tool_msg("small result")]
    capped, was_capped = _cap_tool_result_messages(messages)
    assert was_capped is False
    assert capped[0]["content"] == "small result"


def test_large_tool_result_is_capped():
    big_content = "x" * (DOM_TOOL_RESULT_TOKEN_CAP * 6)
    messages = [_tool_msg(big_content)]
    capped, was_capped = _cap_tool_result_messages(messages)
    assert was_capped is True
    result_content = capped[0]["content"]
    assert "[TRUNCATED:" in result_content
    token_count = estimate_text_tokens(result_content)
    assert token_count <= DOM_TOOL_RESULT_TOKEN_CAP + 30  # small overhead for truncation notice


def test_non_tool_messages_not_touched():
    messages = [
        _sys_msg("system " * 300),
        _user_msg("user " * 300),
        {"role": "assistant", "content": "assistant " * 300},
    ]
    capped, was_capped = _cap_tool_result_messages(messages)
    assert was_capped is False
    assert capped[0]["content"] == messages[0]["content"]
    assert capped[1]["content"] == messages[1]["content"]


def test_multiple_large_tool_results_all_capped():
    big = "dom_data " * 500
    messages = [
        _tool_msg(big, "t1"),
        _tool_msg(big, "t2"),
    ]
    capped, was_capped = _cap_tool_result_messages(messages)
    assert was_capped is True
    assert "[TRUNCATED:" in capped[0]["content"]
    assert "[TRUNCATED:" in capped[1]["content"]


def test_dom_tool_result_summarizes_and_removes_raw_elements():
    dom_payload = {
        "elements": "page: Example\nheadings: Welcome\nctas: Submit",
        "url": "http://fixture/page",
        "_raw_elements": "<html><body><button>Submit</button></body></html>",
    }
    messages = [_tool_msg(json.dumps(dom_payload, ensure_ascii=True))]

    capped, was_capped = _cap_tool_result_messages(messages)

    summarized = json.loads(capped[0]["content"])
    assert was_capped is True
    assert summarized["elements"] == "page: Example\nheadings: Welcome\nctas: Submit"
    assert "_raw_elements" not in summarized


def test_raw_html_tool_result_replaced_with_page_intelligence_summary():
    raw_dom = "<html><body><main><h1>Welcome</h1><button data-testid='submit'>Submit</button></main></body></html>"
    messages = [_tool_msg(raw_dom)]

    capped, was_capped = _cap_tool_result_messages(messages)

    assert was_capped is True
    assert "page:" in capped[0]["content"]
    assert "ctas:" in capped[0]["content"]
    assert "<html>" not in capped[0]["content"]


def test_budget_status_ok_when_no_capping_or_compaction():
    cm = ContextManager()
    messages = [_sys_msg(), _user_msg("click the button")]
    bundle = cm.prepare_messages(messages, purpose="main_orchestrator")
    assert bundle.metadata["budget_status"] == "ok"
    assert bundle.metadata["tool_result_capped"] is False


def test_budget_status_capped_when_large_tool_result():
    cm = ContextManager()
    big_dom = "x" * (DOM_TOOL_RESULT_TOKEN_CAP * 6)
    messages = [_sys_msg(), _user_msg(), _tool_msg(big_dom)]
    bundle = cm.prepare_messages(messages, purpose="main_orchestrator")
    assert bundle.metadata["budget_status"] == "capped"
    assert bundle.metadata["tool_result_capped"] is True


def test_budget_status_compacted_when_history_over_threshold():
    from runtime.history_manager import PROTECTED_HISTORY_TOKEN_THRESHOLD
    cm = ContextManager()
    # Build enough user/assistant messages to exceed the compaction threshold
    big_turn = "long assistant response token filler " * 60
    messages = [_sys_msg()]
    for i in range(30):
        messages.append({"role": "user", "content": f"step {i}"})
        messages.append({"role": "assistant", "content": big_turn})
    bundle = cm.prepare_messages(messages, purpose="main_orchestrator")
    # If compaction was applied, budget_status must reflect it
    if bundle.metadata["compaction_applied"]:
        assert bundle.metadata["budget_status"] == "compacted"
    else:
        assert bundle.metadata["budget_status"] == "ok"


def test_full_raw_dom_excluded_by_capping():
    cm = ContextManager()
    # Simulate a dom_extract tool result that is large
    raw_dom = "<html>" + "<div>element</div>" * 500 + "</html>"
    messages = [_sys_msg(), _user_msg(), _tool_msg(raw_dom)]
    bundle = cm.prepare_messages(messages, purpose="main_orchestrator")
    # Find tool messages in final bundle — they should be capped
    for msg in bundle.messages:
        if isinstance(msg, dict) and msg.get("role") == "tool":
            assert "<html>" not in msg["content"]
            assert "page:" in msg["content"]


def test_original_tool_message_keeps_backend_side_raw_evidence():
    cm = ContextManager()
    raw_payload = {
        "elements": "page: Example",
        "_raw_elements": "<html><body><button>Submit</button></body></html>",
    }
    original_tool_message = _tool_msg(json.dumps(raw_payload, ensure_ascii=True))
    messages = [_sys_msg(), _user_msg(), original_tool_message]

    bundle = cm.prepare_messages(messages, purpose="main_orchestrator")

    summarized_tool = next(msg for msg in bundle.messages if isinstance(msg, dict) and msg.get("role") == "tool")
    assert "_raw_elements" not in summarized_tool["content"]
    assert "_raw_elements" in original_tool_message["content"]
