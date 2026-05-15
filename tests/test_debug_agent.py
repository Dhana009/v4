"""Unit tests for runtime.debug_agent."""
from __future__ import annotations

from dataclasses import fields

import pytest

from runtime.debug_agent import DebugReport, build_debug_report, serialize_debug_report


# ---------------------------------------------------------------------------
# 1. locator_not_found + URL mismatch → locator_replacement repair
# ---------------------------------------------------------------------------

def test_locator_not_found_url_mismatch() -> None:
    failed_step = {
        "step_id": "s1",
        "locator": "//div/button[2]",
        "required_url": "https://app.example.com/checkout",
    }
    page_state = {"url": "https://app.example.com/home", "title": "Home"}
    report = build_debug_report(
        failed_step=failed_step,
        page_state=page_state,
        recent_events=[],
        failure_label="locator_not_found",
    )
    assert "locator" in report.hypothesis.lower() or "locator" in report.suggested_repair.get("kind", "")
    assert report.suggested_repair.get("kind") == "locator_replacement"
    assert report.confidence > 0.0


# ---------------------------------------------------------------------------
# 2. timeout label → increase_timeout repair kind hint
# ---------------------------------------------------------------------------

def test_timeout_repair_kind() -> None:
    failed_step = {"step_id": "s2", "timeout_ms": 5000}
    page_state = {"url": "https://example.com/"}
    report = build_debug_report(
        failed_step=failed_step,
        page_state=page_state,
        recent_events=[],
        failure_label="timeout",
    )
    assert "timeout" in report.suggested_repair.get("kind", "")
    assert report.confidence > 0.0


# ---------------------------------------------------------------------------
# 3. Empty inputs → fallback report with confidence 0.0
# ---------------------------------------------------------------------------

def test_empty_inputs_fallback_report() -> None:
    report = build_debug_report(
        failed_step={},
        page_state={},
        recent_events=[],
        failure_label=None,
    )
    assert isinstance(report, DebugReport)
    assert report.confidence == 0.0
    assert "insufficient" in report.hypothesis.lower() or "unknown" in report.hypothesis.lower()


# ---------------------------------------------------------------------------
# 4. serialize_debug_report keys match DebugReport fields
# ---------------------------------------------------------------------------

def test_serialize_debug_report_keys() -> None:
    report = build_debug_report(
        failed_step={"locator": "#btn"},
        page_state={"url": "https://x.com/"},
        recent_events=[],
        failure_label="locator_not_found",
    )
    serialized = serialize_debug_report(report)
    field_names = {f.name for f in fields(DebugReport)}
    assert field_names == set(serialized.keys())


# ---------------------------------------------------------------------------
# 5. evidence list is populated when failure_label is provided
# ---------------------------------------------------------------------------

def test_evidence_populated_for_labelled_failure() -> None:
    report = build_debug_report(
        failed_step={"locator": "#submit"},
        page_state={"url": "https://x.com/"},
        recent_events=[],
        failure_label="assertion_failure",
    )
    assert len(report.evidence) >= 1


# ---------------------------------------------------------------------------
# 6. Repair dict is empty dict for unknown fallback
# ---------------------------------------------------------------------------

def test_repair_empty_on_fallback() -> None:
    report = build_debug_report(
        failed_step={},
        page_state={},
        recent_events=[],
    )
    assert report.suggested_repair == {}
