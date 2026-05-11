from __future__ import annotations

from runtime.recovery_context import (
    build_recovery_diagnoser_context_payload,
    collect_retry_attempts_for_failed_step,
    extract_recovery_diagnoser_context_from_messages,
    render_recovery_diagnoser_context,
)


def test_collect_retry_attempts_filters_by_failed_step() -> None:
    attempts = [
        {"failed_step_id": "step-1", "status": "retrying", "summary": "retry with visibility check"},
        {"failed_step_id": "step-2", "status": "retrying", "summary": "ignore this retry"},
    ]

    collected = collect_retry_attempts_for_failed_step(attempts, "step-1")

    assert len(collected) == 1
    assert "step_id=step-1" in collected[0]
    assert "ignore this retry" not in collected[0]


def test_recovery_context_payload_tracks_failed_step_and_recent_evidence() -> None:
    payload = build_recovery_diagnoser_context_payload(
        run_id="run-1",
        failed_step_state={
            "step_id": "step-1",
            "operation_id": "op-1",
            "last_error": "timeout while clicking",
        },
        failed_step_id="step-1",
        failed_operation_id="op-1",
        error_summary="timeout while clicking",
        current_page="http://fixture/current | Fixture page",
        user_recovery_instruction="retry safely",
        retry_attempts=[
            {"failed_step_id": "step-1", "status": "retrying", "summary": "wait and retry"},
            {"failed_step_id": "step-2", "status": "retrying", "summary": "unrelated retry"},
        ],
        messages=[
            {"role": "user", "content": "The click failed with a timeout."},
            {"role": "assistant", "content": "Recovery: retry after checking visibility."},
        ],
    )

    assert payload["run_id"] == "run-1"
    assert payload["failed_step_id"] == "step-1"
    assert payload["failed_operation_id"] == "op-1"
    assert payload["error_summary"] == "timeout while clicking"
    assert payload["current_page"] == "http://fixture/current | Fixture page"
    assert "retry safely" in payload["user_recovery_instruction"]
    assert "step_id=step-1" in payload["retry_attempts"]
    assert "step-2" not in payload["retry_attempts"]


def test_recovery_context_renders_compact_and_round_trips() -> None:
    payload = build_recovery_diagnoser_context_payload(
        run_id="run-1",
        failed_step_state={
            "step_id": "step-1",
            "operation_id": "op-1",
            "last_error": "timeout while clicking",
        },
        failed_step_id="step-1",
        error_summary="timeout while clicking",
        current_page="http://fixture/current | Fixture page",
        messages=[
            {"role": "user", "content": "please continue recovery"},
            {"role": "assistant", "content": "Recovery: retry after checking visibility."},
        ],
    )

    rendered = render_recovery_diagnoser_context(payload)
    extracted = extract_recovery_diagnoser_context_from_messages(
        [{"role": "user", "content": rendered}],
        metadata={"run_id": "run-1"},
    )

    assert "DYNAMIC_RECOVERY_CONTEXT:" in rendered
    assert "Recovery required for the failed original step." in rendered
    assert "timeout while clicking" in rendered
    assert "<html" not in rendered.lower()
    assert extracted["failed_step_id"] == "step-1"
    assert extracted["error_summary"] == "timeout while clicking"
