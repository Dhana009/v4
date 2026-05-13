"""
tests/test_plan_diff_events.py

Sprint 7 Cluster 2 — S7-0204: plan_diff event naming and payload alignment.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_plan_diff_proposed_event,
    build_plan_diff_validated_event,
    build_plan_diff_applied_event,
)


# ---------------------------------------------------------------------------
# Unit Tests — plan_diff_proposed
# ---------------------------------------------------------------------------

def test_plan_diff_proposed_type_correct():  # S7-0204
    result = build_plan_diff_proposed_event(
        plan_id="plan-1",
        old_version=1,
        new_version=2,
        operations=[{"op": "add", "step_index": 0, "details": "new step"}],
    )
    assert result["type"] == "plan_diff_proposed"


def test_plan_diff_proposed_includes_plan_id():  # S7-0204
    result = build_plan_diff_proposed_event(
        plan_id="plan-abc",
        old_version=1,
        new_version=2,
        operations=[],
    )
    assert result["plan_id"] == "plan-abc"


def test_plan_diff_proposed_includes_old_new_version():  # S7-0204
    result = build_plan_diff_proposed_event(
        plan_id="plan-1",
        old_version=3,
        new_version=4,
        operations=[],
    )
    assert result["old_version"] == 3
    assert result["new_version"] == 4


def test_plan_diff_proposed_includes_operations():  # S7-0204
    ops = [{"op": "modify", "step_index": 1, "details": "changed action"}]
    result = build_plan_diff_proposed_event(
        plan_id="plan-1", old_version=1, new_version=2, operations=ops
    )
    assert isinstance(result["operations"], list)
    assert len(result["operations"]) == 1


def test_plan_diff_proposed_uses_backend_envelope():  # S7-0204
    result = build_plan_diff_proposed_event(
        plan_id="plan-1", old_version=1, new_version=2, operations=[]
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_plan_diff_proposed_schema_version():  # GOV-S7-C0-007
    result = build_plan_diff_proposed_event(
        plan_id="plan-1", old_version=1, new_version=2, operations=[]
    )
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Unit Tests — plan_diff_validated
# ---------------------------------------------------------------------------

def test_plan_diff_validated_type_correct():  # S7-0204
    result = build_plan_diff_validated_event(
        plan_id="plan-1",
        validation_status="valid",
        issues=[],
    )
    assert result["type"] == "plan_diff_validated"


def test_plan_diff_validated_includes_status():  # S7-0204
    result = build_plan_diff_validated_event(
        plan_id="plan-1", validation_status="invalid", issues=["missing step"]
    )
    assert result["validation_status"] == "invalid"


def test_plan_diff_validated_includes_issues():  # S7-0204
    result = build_plan_diff_validated_event(
        plan_id="plan-1", validation_status="invalid", issues=["missing step", "bad op"]
    )
    assert len(result["issues"]) == 2


def test_plan_diff_validated_uses_backend_envelope():  # S7-0204
    result = build_plan_diff_validated_event(
        plan_id="plan-1", validation_status="valid", issues=[]
    )
    assert "schema_version" in result
    assert "payload" in result


# ---------------------------------------------------------------------------
# Unit Tests — plan_diff_applied
# ---------------------------------------------------------------------------

def test_plan_diff_applied_type_correct():  # S7-0204
    result = build_plan_diff_applied_event(plan_id="plan-1", result="success")
    assert result["type"] == "plan_diff_applied"


def test_plan_diff_applied_includes_plan_id():  # S7-0204
    result = build_plan_diff_applied_event(plan_id="plan-xyz", result="success")
    assert result["plan_id"] == "plan-xyz"


def test_plan_diff_applied_includes_result():  # S7-0204
    result = build_plan_diff_applied_event(plan_id="plan-1", result="failed")
    assert result["result"] in {"success", "failed"}


def test_plan_diff_applied_uses_backend_envelope():  # S7-0204
    result = build_plan_diff_applied_event(plan_id="plan-1", result="success")
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


# ---------------------------------------------------------------------------
# Contract Tests — discussion-only must not mutate plan
# ---------------------------------------------------------------------------

def test_plan_diff_proposed_does_not_mutate_plan():  # S7-0204
    # plan_diff_proposed is advisory — type must not claim execution
    result = build_plan_diff_proposed_event(
        plan_id="plan-1", old_version=1, new_version=2, operations=[]
    )
    assert result["type"] == "plan_diff_proposed"
    assert result["type"] != "plan_ready"
    assert result["type"] != "step_recorded"


def test_plan_diff_proposed_requires_confirmation_before_apply():  # S7-0204
    # The event type alone must not be plan_diff_applied
    proposed = build_plan_diff_proposed_event(
        plan_id="plan-1", old_version=1, new_version=2, operations=[]
    )
    assert proposed["type"] != "plan_diff_applied"


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_plan_diff_proposed_rejects_empty_plan_id():  # S7-0204
    with pytest.raises(ValueError, match="plan_id"):
        build_plan_diff_proposed_event(
            plan_id="", old_version=1, new_version=2, operations=[]
        )


def test_plan_diff_proposed_rejects_none_operations():  # S7-0204
    with pytest.raises((ValueError, TypeError)):
        build_plan_diff_proposed_event(
            plan_id="plan-1", old_version=1, new_version=2, operations=None  # type: ignore
        )


def test_plan_diff_validated_rejects_empty_plan_id():  # S7-0204
    with pytest.raises(ValueError, match="plan_id"):
        build_plan_diff_validated_event(plan_id="", validation_status="valid", issues=[])


def test_plan_diff_validated_rejects_empty_status():  # S7-0204
    with pytest.raises(ValueError, match="validation_status"):
        build_plan_diff_validated_event(plan_id="plan-1", validation_status="", issues=[])


def test_plan_diff_applied_rejects_empty_plan_id():  # S7-0204
    with pytest.raises(ValueError, match="plan_id"):
        build_plan_diff_applied_event(plan_id="", result="success")


def test_plan_diff_applied_rejects_empty_result():  # S7-0204
    with pytest.raises(ValueError, match="result"):
        build_plan_diff_applied_event(plan_id="plan-1", result="")
