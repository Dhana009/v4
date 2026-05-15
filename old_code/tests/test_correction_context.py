from __future__ import annotations

from runtime.correction_context import (
    build_plan_diff_editor_context_payload,
    correction_needs_locator_context,
    extract_plan_diff_editor_context_from_messages,
    render_plan_diff_editor_context,
)


def test_plan_diff_editor_context_payload_tracks_active_plan_and_locator_change() -> None:
    payload = build_plan_diff_editor_context_payload(
        active_plan_state={
            "plan_id": "plan-1",
            "summary": "I will click Get started",
            "steps": [
                {
                    "step_id": "step-1",
                    "intent": "Click the Get started button",
                    "children": [
                        {
                            "operation_id": "op-1",
                            "type": "click",
                            "target": "Get started",
                            "locator": 'get_by_text("Get started", exact=True)',
                        }
                    ],
                }
            ],
        },
        correction_state={
            "target_step_id": "step-1",
            "correction_text": "Use a different locator for the button",
            "allowed_edit_policy": "preserve existing child operations",
        },
        validation_feedback="Keep the current order",
        validated_locators=['get_by_text("Get started", exact=True)'],
    )

    assert payload["active_plan_id"] == "plan-1"
    assert payload["target_step_id"] == "step-1"
    assert payload["active_plan_summary"] == "I will click Get started"
    assert "op-1" in payload["child_operations"]
    assert payload["validation_feedback"] == "Keep the current order"
    assert payload["locator_context_required"] == "yes"
    assert correction_needs_locator_context(
        "Use a different locator for the button",
        correction_state={"explicit_target_change": True},
    )


def test_plan_diff_editor_context_renders_compact_without_dom_or_history() -> None:
    payload = build_plan_diff_editor_context_payload(
        active_plan_state={
            "plan_id": "plan-1",
            "summary": "I will click Get started",
            "steps": [
                {
                    "step_id": "step-1",
                    "intent": "Click the Get started button",
                    "children": [
                        {
                            "operation_id": "op-1",
                            "type": "click",
                            "target": "Get started",
                        }
                    ],
                }
            ],
        },
        correction_state={
            "target_step_id": "step-1",
            "correction_text": "add an assertion first",
        },
    )

    rendered = render_plan_diff_editor_context(payload)
    extracted = extract_plan_diff_editor_context_from_messages(
        [{"role": "user", "content": rendered}],
        active_plan_state=None,
        correction_state=None,
    )

    assert "DYNAMIC_CORRECTION_CONTEXT:" in rendered
    assert "Structured correction diff context." in rendered
    assert "<html" not in rendered.lower()
    assert "browser history" not in rendered.lower()
    assert extracted["active_plan_id"] == "plan-1"
    assert extracted["target_step_id"] == "step-1"
    assert extracted["correction_text"] == "add an assertion first"
