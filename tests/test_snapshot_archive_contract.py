from __future__ import annotations

import pytest

from runtime import spec_snapshot


def _build_archive_snapshot(
    recorded_steps: list[dict[str, object]],
    *,
    completed_step_count: int = 0,
    phase: str = "executing",
) -> dict[str, object]:
    return spec_snapshot.build_spec_snapshot(
        schema_version="autoworkbench.spec.v1",
        session_id="run-archive-001",
        created_at="2026-05-07T00:00:00+00:00",
        original_user_intent="Check that the snapshot archive remains backend-owned",
        plan_ready={
            "summary": "Check that the snapshot archive remains backend-owned",
            "steps": [
                {
                    "number": 1,
                    "action": "assert",
                    "element_name": "Get started",
                    "expected_outcome": {
                        "type": "visibility",
                        "description": "Get started is visible",
                        "source": "user",
                        "required": True,
                    },
                }
            ],
        },
        recorded_steps=recorded_steps,
        code_update_payloads=[],
        capability_gaps=[],
        phase=phase,
        completed_step_count=completed_step_count,
        recorded_step_count=len(recorded_steps),
    )


def _snapshot_loader() -> object | None:
    loader = getattr(spec_snapshot, "load_snapshot_archive", None)
    if callable(loader):
        return loader
    loader = getattr(spec_snapshot, "load_spec_snapshot", None)
    if callable(loader):
        return loader
    return None


def test_snapshot_archive_preserves_recorded_steps_verbatim() -> None:
    recorded_steps = [
        {
            "step_id": "step-1",
            "step_number": 1,
            "intent": "Check that Get started is visible and click it",
            "status": "recorded",
            "generated_line": "await expect(getStarted).toBeVisible();",
            "children": [
                {
                    "kind": "assertion",
                    "code_lines": ["await expect(getStarted).toBeVisible();"],
                }
            ],
        }
    ]

    snapshot = _build_archive_snapshot(recorded_steps, completed_step_count=1)

    assert snapshot["recorded_steps"] == recorded_steps
    assert snapshot["metadata"]["recorded_step_count"] == 1
    assert snapshot["code"]["lines"] == ["await expect(getStarted).toBeVisible();"]
    assert snapshot["code"]["full_spec_preview"] == "await expect(getStarted).toBeVisible();"


def test_snapshot_archive_preserves_expected_outcome_as_step_metadata() -> None:
    expected_outcome = {
        "type": "visibility",
        "description": "Get started is visible",
        "source": "user",
        "required": True,
    }
    recorded_steps = [
        {
            "step_id": "step-1",
            "step_number": 1,
            "intent": "Check that Get started is visible and click it",
            "status": "recorded",
            "expected_outcome": expected_outcome,
            "generated_line": "await expect(getStarted).toBeVisible();",
        }
    ]

    snapshot = _build_archive_snapshot(recorded_steps)

    assert snapshot["recorded_steps"][0]["expected_outcome"] == expected_outcome
    assert snapshot["plan_ready"]["steps"][0]["expected_outcome"] == {
        "type": "visibility",
        "description": "Get started is visible",
        "source": "user",
        "required": True,
    }
    assert snapshot["code"]["lines"] == ["await expect(getStarted).toBeVisible();"]


def test_snapshot_archive_preserves_observed_outcome_when_present() -> None:
    observed_outcome = {
        "matched_expected": True,
        "before_url": "http://example.test/before",
        "after_url": "http://example.test/after",
        "before_title": "Before",
        "after_title": "After",
    }
    recorded_steps = [
        {
            "step_id": "step-1",
            "step_number": 1,
            "intent": "Check that Get started is visible and click it",
            "status": "recorded",
            "observed_outcome": observed_outcome,
            "generated_line": "await expect(getStarted).toBeVisible();",
        }
    ]

    snapshot = _build_archive_snapshot(recorded_steps)

    assert snapshot["recorded_steps"][0]["observed_outcome"] == observed_outcome
    assert snapshot["metadata"]["recorded_step_count"] == 1
    assert snapshot["code"]["lines"] == ["await expect(getStarted).toBeVisible();"]


def test_loading_snapshot_archive_does_not_mark_unresolved_steps_complete() -> None:
    loader = _snapshot_loader()
    if loader is None:
        pytest.xfail("No backend snapshot archive loader/reconstructor seam yet")

    archive = {
        "schema_version": "autoworkbench.spec.v1",
        "session_id": "run-archive-001",
        "created_at": "2026-05-07T00:00:00+00:00",
        "recorded_steps": [
            {"step_id": "step-open", "status": "recorded"},
            {"step_id": "step-failed", "status": "failed"},
            {"step_id": "step-done", "status": "completed"},
        ],
        "metadata": {"phase": "recovering", "completed_step_count": 1, "recorded_step_count": 3},
    }

    restored = loader(archive)

    if isinstance(restored, dict):
        completed_step_ids = set(restored.get("completed_step_ids") or [])
        assert "step-open" not in completed_step_ids
        assert "step-failed" not in completed_step_ids
        assert restored.get("pending_recovery") is not True
        return

    pytest.fail(f"Unexpected snapshot loader result type: {type(restored).__name__}")


def test_corrupted_snapshot_archive_input_is_rejected_safely() -> None:
    loader = _snapshot_loader()
    if loader is None:
        pytest.xfail("No backend snapshot archive loader/reconstructor seam yet")

    bad_archives = [
        None,
        {},
        {"schema_version": "autoworkbench.spec.v1"},
        {"session_id": "run-archive-001"},
    ]

    for bad_archive in bad_archives:
        try:
            restored = loader(bad_archive)  # type: ignore[arg-type]
        except Exception:
            continue

        if isinstance(restored, dict):
            assert restored.get("ok") is False or restored.get("error")
            continue

        pytest.fail(f"Unexpected snapshot loader result type: {type(restored).__name__}")
