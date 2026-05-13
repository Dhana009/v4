"""
tests/test_recommendation_event_pipeline.py

Sprint 7 Cluster 2 — S7-0202: recommendation_ready backend event pipeline.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_recommendation_ready_event,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_recommendation_ready_includes_request_id():  # S7-0202
    result = build_recommendation_ready_event(
        request_id="req-1",
        recommendations=[],
    )
    assert result["request_id"] == "req-1"


def test_recommendation_ready_type_correct():  # S7-0202
    result = build_recommendation_ready_event(
        request_id="req-1",
        recommendations=[],
    )
    assert result["type"] == "recommendation_ready"


def test_recommendation_ready_includes_recommendations_list():  # S7-0202
    recs = [
        {"id": "r1", "type": "assertion", "target": "#btn", "reason": "visible", "confidence": 0.9}
    ]
    result = build_recommendation_ready_event(request_id="req-1", recommendations=recs)
    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) == 1


def test_recommendation_ready_includes_timestamp():  # S7-0202
    result = build_recommendation_ready_event(request_id="req-1", recommendations=[])
    assert "timestamp" in result or "emitted_at" in result


def test_recommendation_ready_uses_backend_envelope():  # S7-0202
    result = build_recommendation_ready_event(request_id="req-1", recommendations=[])
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_recommendation_ready_schema_version():  # GOV-S7-C0-007
    result = build_recommendation_ready_event(request_id="req-1", recommendations=[])
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Contract Tests — payload fields
# ---------------------------------------------------------------------------

def test_recommendation_ready_preserves_recommendation_fields():  # S7-0202
    recs = [
        {
            "id": "r1",
            "type": "click",
            "target": "#submit",
            "reason": "primary CTA",
            "confidence": 0.85,
        }
    ]
    result = build_recommendation_ready_event(request_id="req-1", recommendations=recs)
    first = result["recommendations"][0]
    assert first["id"] == "r1"
    assert first["confidence"] == 0.85


def test_recommendation_ready_empty_list_is_safe():  # S7-0202
    result = build_recommendation_ready_event(request_id="req-1", recommendations=[])
    assert result["recommendations"] == []


def test_recommendation_ready_filters_low_confidence_when_threshold_set():  # S7-0202
    recs = [
        {"id": "r1", "confidence": 0.9, "type": "click", "target": "#a"},
        {"id": "r2", "confidence": 0.3, "type": "fill", "target": "#b"},
    ]
    result = build_recommendation_ready_event(
        request_id="req-1", recommendations=recs, min_confidence=0.5
    )
    ids = [r["id"] for r in result["recommendations"]]
    assert "r1" in ids
    assert "r2" not in ids


def test_recommendation_ready_no_autoexecution():  # GOV-S7-C2
    result = build_recommendation_ready_event(
        request_id="req-1",
        recommendations=[{"id": "r1", "type": "click", "target": "#btn"}],
    )
    assert result["type"] == "recommendation_ready"
    assert result["type"] != "step_recorded"
    assert result["type"] != "run_completed"


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_recommendation_ready_rejects_empty_request_id():  # S7-0202
    with pytest.raises(ValueError, match="request_id"):
        build_recommendation_ready_event(request_id="", recommendations=[])


def test_recommendation_ready_rejects_none_recommendations():  # S7-0202
    with pytest.raises((ValueError, TypeError)):
        build_recommendation_ready_event(request_id="req-1", recommendations=None)  # type: ignore


def test_recommendation_ready_deep_copies_input():  # GOV-S7-C0-001
    recs = [{"id": "r1", "confidence": 0.9}]
    result = build_recommendation_ready_event(request_id="req-1", recommendations=recs)
    recs[0]["id"] = "mutated"
    assert result["recommendations"][0]["id"] == "r1"


def test_recommendation_ready_stale_request_id_not_validated_by_builder():  # S7-0202
    # Builder is pure — stale ID validation is caller's responsibility
    result = build_recommendation_ready_event(request_id="req-stale", recommendations=[])
    assert result["request_id"] == "req-stale"
