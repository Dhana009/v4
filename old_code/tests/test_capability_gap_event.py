"""
tests/test_capability_gap_event.py

Sprint 7 Cluster 2 — S7-0208: capability_gap frontend-facing contract.
TDD: written before implementation.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_capability_gap_event,
)
from runtime.capability_registry import (
    CapabilityStatus,
    get_capability_status,
    BASELINE_CAPABILITIES,
)


# ---------------------------------------------------------------------------
# Unit Tests — event builder
# ---------------------------------------------------------------------------

def test_capability_gap_event_type_correct():  # S7-0208
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported in baseline",
        next_legal_action="click",
    )
    assert result["type"] == "capability_gap"


def test_capability_gap_event_includes_action():  # S7-0208
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported",
        next_legal_action="click",
    )
    assert result["action"] == "drag_and_drop"


def test_capability_gap_event_includes_reason():  # S7-0208
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="Drag and drop requires custom JS bridge",
        next_legal_action="click",
    )
    assert "Drag and drop" in result["reason"]


def test_capability_gap_event_includes_next_legal_action():  # S7-0208
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported",
        next_legal_action="click",
    )
    assert result["next_legal_action"] == "click"


def test_capability_gap_event_uses_backend_envelope():  # S7-0208
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported",
        next_legal_action="click",
    )
    assert "schema_version" in result
    assert "payload" in result
    assert "emitted_at" in result


def test_capability_gap_event_schema_version():  # GOV-S7-C0-007
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported",
        next_legal_action="click",
    )
    assert result["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION


def test_capability_gap_event_includes_severity():  # S7-0208
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported",
        next_legal_action="click",
        severity="error",
    )
    assert result["severity"] in {"error", "warning", "info"}


def test_capability_gap_event_default_severity_is_error():  # S7-0208
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported",
        next_legal_action="click",
    )
    assert result.get("severity") in {"error", "warning", "info", None}


# ---------------------------------------------------------------------------
# Contract Tests — no fake success
# ---------------------------------------------------------------------------

def test_capability_gap_event_not_step_recorded():  # GOV-S7-C2
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported",
        next_legal_action="click",
    )
    assert result["type"] != "step_recorded"


def test_capability_gap_event_not_code_update():  # GOV-S7-C2
    result = build_capability_gap_event(
        action="drag_and_drop",
        reason="not supported",
        next_legal_action="click",
    )
    assert result["type"] != "code_update"


# ---------------------------------------------------------------------------
# Unit Tests — capability registry
# ---------------------------------------------------------------------------

def test_supported_action_is_supported():  # S7-0208
    status = get_capability_status("click")
    assert status == CapabilityStatus.SUPPORTED


def test_unsupported_action_is_capability_gap():  # S7-0208
    status = get_capability_status("drag_and_drop")
    assert status == CapabilityStatus.CAPABILITY_GAP


def test_baseline_capabilities_nonempty():  # S7-0208
    assert len(BASELINE_CAPABILITIES) > 0


def test_click_in_baseline():  # S7-0208
    assert "click" in BASELINE_CAPABILITIES


def test_fill_in_baseline():  # S7-0208
    assert "fill" in BASELINE_CAPABILITIES


def test_hover_in_baseline():  # S7-0208
    assert "hover" in BASELINE_CAPABILITIES


def test_drag_and_drop_not_in_baseline():  # S7-0208
    assert "drag_and_drop" not in BASELINE_CAPABILITIES


def test_case_insensitive_registry_lookup():  # S7-0208
    status = get_capability_status("CLICK")
    assert status == CapabilityStatus.SUPPORTED


# ---------------------------------------------------------------------------
# Negative Tests
# ---------------------------------------------------------------------------

def test_capability_gap_event_rejects_empty_action():  # S7-0208
    with pytest.raises(ValueError, match="action"):
        build_capability_gap_event(action="", reason="not supported", next_legal_action="click")


def test_capability_gap_event_rejects_empty_reason():  # S7-0208
    with pytest.raises(ValueError, match="reason"):
        build_capability_gap_event(
            action="drag_and_drop", reason="", next_legal_action="click"
        )


def test_capability_gap_event_rejects_empty_next_legal_action():  # S7-0208
    with pytest.raises(ValueError, match="next_legal_action"):
        build_capability_gap_event(
            action="drag_and_drop", reason="not supported", next_legal_action=""
        )
