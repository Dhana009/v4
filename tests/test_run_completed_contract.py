"""
tests/test_run_completed_contract.py

Sprint 7 Cluster 1 — S7-0106: run_completed frontend-ready payload contract tests.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_run_completed_payload,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_build_run_completed_payload_includes_run_id():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="done", recorded_count=3, skipped_count=0, failed_count=0
    )
    assert result["run_id"] == "run-001"


def test_build_run_completed_payload_includes_recorded_count():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="done", recorded_count=5, skipped_count=0, failed_count=0
    )
    assert result["recorded_count"] == 5


def test_build_run_completed_payload_includes_skipped_count():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="done", recorded_count=3, skipped_count=2, failed_count=0
    )
    assert result["skipped_count"] == 2


def test_build_run_completed_payload_includes_failed_count():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="done", recorded_count=3, skipped_count=0, failed_count=1
    )
    assert result["failed_count"] == 1


def test_build_run_completed_payload_includes_code_status():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="done", recorded_count=3, skipped_count=0, failed_count=0, code_status="generated"
    )
    assert result["code_status"] == "generated"


def test_build_run_completed_payload_includes_summary():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="All steps complete", recorded_count=3, skipped_count=0, failed_count=0
    )
    assert "All steps complete" in result["summary"]


def test_build_run_completed_payload_includes_phase():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="done", recorded_count=3, skipped_count=0, failed_count=0
    )
    assert result.get("phase") == "completed"


def test_build_run_completed_payload_code_status_default():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="done", recorded_count=3, skipped_count=0, failed_count=0
    )
    assert result.get("code_status") in {"not_generated", "generated"}


def test_build_run_completed_payload_failed_count_default_zero():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="run-001", summary="done", recorded_count=3, skipped_count=0
    )
    assert result.get("failed_count", 0) == 0


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------

def test_run_completed_event_type_field_correct():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="r", summary="s", recorded_count=0, skipped_count=0, failed_count=0
    )
    assert result["type"] == "run_completed"


def test_run_completed_uses_backend_event_envelope():  # PRD-04-BE-008
    result = build_run_completed_payload(
        run_id="r", summary="s", recorded_count=0, skipped_count=0, failed_count=0
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_run_completed_payload_fields_are_stable_types():  # PRD-04-BE-008
    # counts are int, code_status is string, run_id is string
    result = build_run_completed_payload(
        run_id="r", summary="s", recorded_count=2, skipped_count=1, failed_count=0
    )
    assert isinstance(result["recorded_count"], int)
    assert isinstance(result["skipped_count"], int)
    assert isinstance(result["run_id"], str)
    assert isinstance(result.get("code_status", ""), str)


# ---------------------------------------------------------------------------
# Integration / Ordering Tests
# ---------------------------------------------------------------------------

def test_run_completed_counts_sum_to_total_steps():  # PRD-04-BE-008
    # recorded_count + skipped_count + failed_count = total steps processed
    result = build_run_completed_payload(
        run_id="r", summary="s", recorded_count=3, skipped_count=1, failed_count=1
    )
    total = result["recorded_count"] + result["skipped_count"] + result["failed_count"]
    assert total == 5


# ---------------------------------------------------------------------------
# Negative Tests (required by GOV-S7-C0-009)
# ---------------------------------------------------------------------------

def test_build_run_completed_rejects_empty_run_id():  # PRD-04-BE-008
    with pytest.raises(ValueError, match="run_id"):
        build_run_completed_payload(
            run_id="", summary="done", recorded_count=0, skipped_count=0, failed_count=0
        )


def test_build_run_completed_rejects_negative_recorded_count():  # PRD-04-BE-008
    with pytest.raises((ValueError, AssertionError)):
        build_run_completed_payload(
            run_id="r", summary="s", recorded_count=-1, skipped_count=0, failed_count=0
        )


def test_build_run_completed_rejects_negative_failed_count():  # PRD-04-BE-008
    with pytest.raises((ValueError, AssertionError)):
        build_run_completed_payload(
            run_id="r", summary="s", recorded_count=0, skipped_count=0, failed_count=-1
        )


def test_build_run_completed_rejects_negative_skipped_count():  # PRD-04-BE-008
    with pytest.raises((ValueError, AssertionError)):
        build_run_completed_payload(
            run_id="r", summary="s", recorded_count=0, skipped_count=-1, failed_count=0
        )


def test_build_run_completed_rejects_empty_summary():  # PRD-04-BE-008
    with pytest.raises(ValueError, match="summary"):
        build_run_completed_payload(
            run_id="run-001", summary="", recorded_count=0, skipped_count=0, failed_count=0
        )
