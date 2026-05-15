"""
tests/test_locator_candidates_event.py

Sprint 7 Cluster 2 — S7-0205: locator_specialist frontend-facing payload alignment.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_locator_candidates_ready_event,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_locator_candidates_ready_type_correct():  # S7-0205
    result = build_locator_candidates_ready_event(
        ambiguity_id="amb-1",
        candidates=[],
    )
    assert result["type"] == "locator_candidates_ready"


def test_locator_candidates_ready_includes_ambiguity_id():  # S7-0205
    result = build_locator_candidates_ready_event(
        ambiguity_id="amb-xyz",
        candidates=[],
    )
    assert result["ambiguity_id"] == "amb-xyz"


def test_locator_candidates_ready_includes_candidates_list():  # S7-0205
    candidates = [
        {
            "id": "c1",
            "label": "Submit",
            "role": "button",
            "section": "main",
            "scope": "exact",
            "risk": "low",
            "locator_preview": "[data-testid=submit]",
            "confidence": 0.9,
        }
    ]
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=candidates)
    assert isinstance(result["candidates"], list)
    assert len(result["candidates"]) == 1


def test_locator_candidates_ready_candidate_has_required_fields():  # S7-0205
    candidates = [
        {
            "id": "c1",
            "label": "Submit",
            "role": "button",
            "section": "main",
            "scope": "exact",
            "risk": "low",
            "locator_preview": "[type=submit]",
            "confidence": 0.9,
        }
    ]
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=candidates)
    c = result["candidates"][0]
    for field in ("id", "label", "scope", "risk", "locator_preview", "confidence"):
        assert field in c, f"candidate missing field: {field}"


def test_locator_candidates_ready_uses_backend_envelope():  # S7-0205
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=[])
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_locator_candidates_ready_schema_version():  # GOV-S7-C0-007
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=[])
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_locator_candidates_no_raw_dom():  # GOV-S7-C2
    candidates = [
        {
            "id": "c1",
            "label": "btn",
            "role": "button",
            "section": "main",
            "scope": "exact",
            "risk": "low",
            "locator_preview": "#btn",
            "confidence": 0.8,
            "raw_dom": "<button>Submit</button>",
        }
    ]
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=candidates)
    import json
    payload_str = json.dumps(result)
    assert "raw_dom" not in payload_str


def test_locator_candidates_candidate_not_auto_activated():  # GOV-S7-C2
    result = build_locator_candidates_ready_event(
        ambiguity_id="amb-1",
        candidates=[{"id": "c1", "label": "btn", "locator_preview": "#btn", "confidence": 0.9}],
    )
    assert result["type"] == "locator_candidates_ready"
    assert result["type"] != "step_recorded"
    assert result["type"] != "step_executing"


def test_locator_candidates_ready_includes_timestamp():  # S7-0205
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=[])
    assert "timestamp" in result or "emitted_at" in result


# ---------------------------------------------------------------------------
# Contract Tests — stable IDs
# ---------------------------------------------------------------------------

def test_locator_candidates_stable_ids_preserved():  # S7-0205
    candidates = [
        {"id": "c-stable-1", "label": "Login", "confidence": 0.8},
        {"id": "c-stable-2", "label": "Register", "confidence": 0.7},
    ]
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=candidates)
    ids = [c["id"] for c in result["candidates"]]
    assert "c-stable-1" in ids
    assert "c-stable-2" in ids


def test_locator_candidates_deep_copied():  # GOV-S7-C0-001
    candidates = [{"id": "c1", "label": "btn", "confidence": 0.9}]
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=candidates)
    candidates[0]["id"] = "mutated"
    assert result["candidates"][0]["id"] == "c1"


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_locator_candidates_ready_rejects_empty_ambiguity_id():  # S7-0205
    with pytest.raises(ValueError, match="ambiguity_id"):
        build_locator_candidates_ready_event(ambiguity_id="", candidates=[])


def test_locator_candidates_ready_rejects_none_candidates():  # S7-0205
    with pytest.raises((ValueError, TypeError)):
        build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=None)  # type: ignore


def test_locator_candidates_empty_list_is_safe():  # S7-0205
    result = build_locator_candidates_ready_event(ambiguity_id="amb-1", candidates=[])
    assert result["candidates"] == []
